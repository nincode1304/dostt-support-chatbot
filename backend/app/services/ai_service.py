"""
AI service: all Gemini interactions.

Responsibilities:
  1. identify_faq           – structured JSON: which FAQ best matches the user message?
  2. generate_*_response    – natural conversational text based on FAQ answer + context
  3. classify_ticket_intent – does the user's reply mean "yes, create a ticket"?

The backend orchestrates the conversation flow; AI only generates text.
"""

import asyncio
import json
import logging
import re
from typing import List, Optional

from google import genai
from google.genai import types

from app.config import settings
from app.models.faq import FAQ, FeedbackType, IssueType
from app.models.session import ChatMessage, SessionState

logger = logging.getLogger(__name__)

_client = genai.Client(api_key=settings.GEMINI_API_KEY)

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are a friendly support agent for Dostt, a social calling app.
LANGUAGE RULES — follow these strictly:
- Use the simplest, most basic English words possible. Imagine you are talking to someone who barely knows English.
- Write very short sentences. Maximum 1–2 sentences per reply.
- Never use difficult or formal words. Use everyday words only.
- No bullet points, no lists, no markdown, no bold text.
- Only use facts from the FAQ information given. Never make up anything.
- CRITICAL: Never change any numbers, time periods, or amounts from the FAQ facts. If the FAQ says "days", say "days". If it says "24 hours", say "24 hours". Do not replace with your own estimate.
- Never mention FAQs, databases, systems, or that you are an AI.
- Be warm and kind, like a helpful friend.\
"""

_APP_CONTEXT = """\
Dostt app context:
- Users (customers) purchase coins to call Listeners for conversation and support.
- Listeners (experts) earn from completed calls and can withdraw earnings.
- Calls are real-time audio or video sessions.
- Coins are the in-app currency used by customers.
- Listeners complete KYC and receive payouts via UPI.
"""


# ---------------------------------------------------------------------------
# 1. FAQ identification
# ---------------------------------------------------------------------------

async def identify_faq(
    message: str,
    user_type: str,
    faqs: List[FAQ],
) -> Optional[str]:
    """
    Return the FAQ id (as a string of the integer) of the best-matching FAQ,
    or None if no match is found.
    """
    faq_list_text = "\n".join(f"{f.id}: {f.title11}" for f in faqs)

    prompt = (
        f'User support message: "{message}"\n\n'
        f"FAQ options:\n{faq_list_text}\n\n"
        'Return only a JSON object with the best matching FAQ id and your confidence level.\n'
        'Example output: {"id": 364, "confidence": "HIGH"}\n'
        'If nothing matches: {"id": null, "confidence": "NONE"}\n'
        'Output the JSON object only, no other text.'
    )

    for attempt in range(3):
        try:
            response = await _client.aio.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema={
                        "type": "OBJECT",
                        "properties": {
                            "id": {"type": "NUMBER", "nullable": True},
                            "confidence": {"type": "STRING"},
                        },
                        "required": ["id", "confidence"],
                    },
                    max_output_tokens=1024,
                    temperature=0.0,
                ),
            )
            if not response.text:
                logger.warning("identify_faq: empty response from model")
                return None
            data = json.loads(response.text)
            faq_id = data.get("id")
            confidence = data.get("confidence", "LOW")
            if faq_id is not None and confidence != "NONE":
                logger.debug("FAQ matched: id=%s (%s)", faq_id, confidence)
                return str(int(faq_id))
            return None
        except Exception as e:
            is_503 = "503" in str(e) or "UNAVAILABLE" in str(e)
            if is_503 and attempt < 2:
                wait = 2 ** attempt
                logger.warning("identify_faq 503, retrying in %ss (attempt %d/2)", wait, attempt + 1)
                await asyncio.sleep(wait)
                continue
            logger.error("identify_faq error: %s", e)
            raise


# ---------------------------------------------------------------------------
# 2. Response generation
# ---------------------------------------------------------------------------

def _faq_to_facts(answer_plain: str) -> str:
    """Break the FAQ plain text into a key-facts bullet list.
    Passing facts as bullets instead of prose avoids Gemini's recitation filter."""
    sentences = re.split(r"(?<=[.!?])\s+", answer_plain.strip())
    facts = [s.strip() for s in sentences if len(s.strip()) > 10]
    return "\n".join(f"- {f}" for f in facts)


def _format_history(messages: List[ChatMessage]) -> List[types.Content]:
    contents = []
    for m in messages[-10:]:
        role = "user" if m.role == "user" else "model"
        contents.append(types.Content(role=role, parts=[types.Part(text=m.content)]))
    return contents


async def generate_initial_response(
    faq: FAQ,
    original_message: str,
    session: SessionState,
    context_note: Optional[str] = None,
) -> str:
    context_parts = [
        f"User type: {session.user_type.value}",
        f"User's message: \"{original_message}\"",
        f"Issue topic: {faq.title11}",
        f"Key facts to convey:\n{_faq_to_facts(faq.answer_plain)}",
    ]
    if context_note:
        context_parts.append(f"Note: {context_note}")

    context = "\n\n".join(context_parts)

    if faq.type in (IssueType.CALL, IssueType.PAYMENT):
        entity = "calls" if faq.type == IssueType.CALL else "transactions"
        instruction = (
            f"In 1 simple sentence, tell the user you understand their problem. "
            f"In 1 more simple sentence, tell them you are showing their recent {entity} so they can pick the right one. "
            f"Use very easy words. Do NOT answer the question yet."
        )
    else:
        if faq.feedback_type == FeedbackType.FEEDBACK_ONLY:
            instruction = (
                "Using only the key facts given, explain the answer to the user in very simple words. "
                "Write like you are talking to someone who does not know much English. "
                "Use 2 short sentences only. Do not copy the FAQ text — say it in your own easy words."
            )
        else:  # RAISE_COMPLAINT_ONLY or BOTH — answer first, system will ask about ticket after
            instruction = (
                "Using only the key facts given, explain the answer to the user in very simple words. "
                "Write like you are talking to someone who does not know much English. "
                "Use 2 short sentences only. Do not copy the FAQ text — say it in your own easy words. "
                "Do not mention tickets or next steps."
            )

    prompt = f"{_APP_CONTEXT}\n\n{context}\n\nInstruction: {instruction}"
    return await _call_gemini(prompt, session.messages)


async def generate_post_selection_response(
    faq: FAQ,
    session: SessionState,
    selection_summary: str,
) -> str:
    context = (
        f"User type: {session.user_type.value}\n"
        f"Original issue: \"{session.original_message}\"\n"
        f"Issue topic: {faq.title11}\n"
        f"Selected item: {selection_summary}\n"
        f"Key facts to convey:\n{_faq_to_facts(faq.answer_plain)}"
    )

    if faq.feedback_type == FeedbackType.FEEDBACK_ONLY:
        instruction = (
            "Using only the key facts given, explain the answer in very simple, easy words. "
            "Mention the specific call or transaction in 1 short sentence if it helps. "
            "Write like you are talking to someone who does not know much English. 2 sentences max."
        )
    elif faq.feedback_type == FeedbackType.RAISE_COMPLAINT_ONLY:
        instruction = (
            "In 1 simple sentence, show that you understand the user's problem with this specific item. "
            "Use very easy words. Do not mention tickets or next steps."
        )
    else:  # BOTH
        instruction = (
            "In 1 simple sentence, show that you understand the user's problem with this specific item. "
            "In 1 more simple sentence, explain the answer using only the key facts given. "
            "Use the exact time periods and numbers from the key facts — do not change them. "
            "Use very easy words. Do not mention tickets or next steps."
        )

    prompt = f"{_APP_CONTEXT}\n\n{context}\n\nInstruction: {instruction}"
    return await _call_gemini(prompt, session.messages)


async def generate_no_faq_response(message: str, user_type: str) -> str:
    prompt = (
        f"A {user_type} sent: \"{message}\"\n\n"
        "You could not find a matching FAQ for their issue. "
        "Apologise briefly, say you don't have information about that topic, "
        "and suggest they raise a support ticket so a human agent can help. "
        "2 sentences maximum."
    )
    return await _call_gemini(prompt, [])


async def generate_already_ended_response() -> str:
    return (
        "It looks like our previous conversation has ended. "
        "Feel free to send a new message if you need help with anything else!"
    )


# ---------------------------------------------------------------------------
# 3. Ticket intent classification
# ---------------------------------------------------------------------------

async def classify_ticket_intent(message: str) -> bool:
    prompt = (
        f"User message: \"{message}\"\n\n"
        "Does this mean the user wants to create a support ticket or get further help? "
        "Reply with only: YES or NO"
    )
    try:
        response = await _client.aio.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction="You classify intent. Reply only YES or NO.",
                max_output_tokens=5,
                temperature=0.0,
            ),
        )
        return response.text.strip().upper().startswith("Y")
    except Exception as e:
        logger.error("classify_ticket_intent error: %s", e)
        return False


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------

async def _call_gemini(
    user_prompt: str,
    history: List[ChatMessage],
    max_tokens: int = 8192,
    _retries: int = 2,
) -> str:
    contents = _format_history(history)
    contents.append(types.Content(role="user", parts=[types.Part(text=user_prompt)]))

    for attempt in range(_retries + 1):
        try:
            response = await _client.aio.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=_SYSTEM_PROMPT,
                    max_output_tokens=max_tokens,
                    temperature=0.5,
                ),
            )
            candidate = response.candidates[0] if response.candidates else None
            finish = candidate.finish_reason if candidate else "UNKNOWN"
            text = response.text
            logger.info("Model response | finish_reason=%s | text=%r", finish, text)
            if not text:
                logger.warning("Empty response from model, finish_reason=%s", finish)
                raise ValueError(f"Model returned empty response (finish_reason={finish})")
            return text.strip()
        except Exception as e:
            is_503 = "503" in str(e) or "UNAVAILABLE" in str(e)
            if is_503 and attempt < _retries:
                wait = 2 ** attempt  # 1s, then 2s
                logger.warning("Gemini 503, retrying in %ss (attempt %d/%d)", wait, attempt + 1, _retries)
                await asyncio.sleep(wait)
                continue
            logger.error("Gemini API error: %s", e)
            raise
