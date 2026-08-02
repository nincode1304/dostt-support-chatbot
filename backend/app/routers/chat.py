"""
Chat router: orchestrates the full conversation state machine.

The AI only generates text. All flow decisions (which stage, which cards to
show, when to create a ticket) are made deterministically here.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, HTTPException

from app.models.chat import (
    ChatRequest,
    ChatResponse,
    InitSessionRequest,
    InitSessionResponse,
    MessageInputType,
    ResponseItem,
    ResponseItemType,
)
from app.models.faq import FeedbackType, IssueType
from app.models.session import ChatMessage, ConversationStage, SessionState
from app.services import ai_service, faq_service, session_service
from app.services import dostt_client
from app.services.dostt_client import DUMMY_MODE

router = APIRouter(prefix="/api", tags=["chat"])
logger = logging.getLogger(__name__)

# ── Change this to allow more or fewer tickets per chat session ───────────────
MAX_TICKETS_PER_SESSION = 2
# ─────────────────────────────────────────────────────────────────────────────


# ---------------------------------------------------------------------------
# Session init
# ---------------------------------------------------------------------------

@router.post("/session/init", response_model=InitSessionResponse)
async def init_session(req: InitSessionRequest) -> InitSessionResponse:
    session = session_service.create_session(
        auth_token=req.auth_token,
        user_type=req.user_type,
    )
    greeting = (
        "Hi! I'm Dostt Support. I'm here to help you with any questions or issues "
        "you're facing with the app. What can I help you with today?"
    )
    return InitSessionResponse(session_id=session.session_id, greeting=greeting)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@router.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


# ---------------------------------------------------------------------------
# Main chat endpoint
# ---------------------------------------------------------------------------

@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    session = session_service.get_session(req.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found or expired.")

    # Record user's text message in history
    if req.type == MessageInputType.TEXT and req.message:
        session.messages.append(ChatMessage(role="user", content=req.message))

    try:
        items = await _dispatch(session, req)
    except Exception as e:
        logger.exception("Unhandled error in chat dispatch: %s", e)
        items = [ResponseItem(
            type=ResponseItemType.ERROR,
            content=(
                "I'm sorry, something went wrong on my end. "
                "Please try again or raise a ticket and our team will help you."
            ),
        )]

    # Persist bot text messages in history
    for item in items:
        if item.type == ResponseItemType.TEXT and item.content:
            session.messages.append(ChatMessage(role="assistant", content=item.content))

    session_service.save_session(session)
    return ChatResponse(session_id=session.session_id, items=items)


# ---------------------------------------------------------------------------
# Stage dispatcher
# ---------------------------------------------------------------------------

async def _dispatch(session: SessionState, req: ChatRequest) -> List[ResponseItem]:
    stage = session.stage

    if stage == ConversationStage.INITIAL:
        return await _handle_initial(session, req)

    if stage == ConversationStage.AWAITING_CALL_SELECTION:
        return await _handle_call_selection(session, req)

    if stage == ConversationStage.AWAITING_TRANSACTION_SELECTION:
        return await _handle_transaction_selection(session, req)

    if stage == ConversationStage.ANSWERED:
        return await _handle_ticket_intent(session, req)

    if stage == ConversationStage.AWAITING_TICKET_CONFIRMATION:
        return await _handle_ticket_confirmation(session, req)

    if stage == ConversationStage.AWAITING_TICKET_EDIT:
        return await _handle_ticket_edit(session, req)

    if stage == ConversationStage.AWAITING_CALL_CONSENT:
        return await _handle_call_consent(session, req)

    # TICKET_CREATED or ENDED — restart if the user sends a new text message
    if req.type == MessageInputType.TEXT and req.message:
        session.stage = ConversationStage.INITIAL
        session.matched_faq_id = None
        session.original_message = None
        session.selected_call = None
        session.selected_transaction = None
        session.ticket_description = None
        session.consent_call = None
        session.messages = []
        return await _handle_initial(session, req)

    text = await ai_service.generate_already_ended_response()
    return [_text(text)]


# ---------------------------------------------------------------------------
# INITIAL: match FAQ and start the appropriate flow
# ---------------------------------------------------------------------------

async def _handle_initial(session: SessionState, req: ChatRequest) -> List[ResponseItem]:
    if not req.message:
        return [_text("Please type your question and I'll do my best to help.")]

    faqs = faq_service.get_faqs_for_user_type(session.user_type)
    issue_id = await ai_service.identify_faq(req.message, session.user_type, faqs)

    if not issue_id:
        session.stage = ConversationStage.ENDED
        return [_text(_out_of_scope_reply())]

    faq = faq_service.get_faq_by_id(issue_id)
    if not faq:
        session.stage = ConversationStage.ENDED
        return [_text(_out_of_scope_reply())]

    session.matched_faq_id = issue_id
    session.original_message = req.message

    if faq.type == IssueType.CALL:
        return await _start_call_flow(session, faq)
    if faq.type == IssueType.PAYMENT:
        return await _start_payment_flow(session, faq)
    if faq.type == IssueType.PAYOUT:
        return await _start_payout_flow(session, faq)
    # OTHER (0) and ALL (3) both follow the direct-answer flow
    return await _handle_other_issue(session, faq)


# ---------------------------------------------------------------------------
# CALL flow
# ---------------------------------------------------------------------------

async def _start_call_flow(session: SessionState, faq) -> List[ResponseItem]:
    if not session.auth_token and not DUMMY_MODE:
        return await _fallback_to_no_data(session, faq, entity="calls")

    try:
        if session.user_type.value == "LISTENER":
            calls = await dostt_client.get_recent_listener_sessions(
                session.auth_token, limit=5
            )
        else:
            calls = await dostt_client.get_recent_calls(session.auth_token, limit=5)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            session.stage = ConversationStage.ENDED
            return [_text(
                "I wasn't able to verify your session. "
                "Please close this chat and reopen it from the Dostt app."
            )]
        return await _fallback_to_no_data(session, faq, entity="calls")
    except Exception:
        return await _fallback_to_no_data(session, faq, entity="calls")

    # Hide calls that already have a ticket raised
    calls = [c for c in calls if not c.get("ticket_detail")]

    if not calls:
        return await _fallback_to_no_data(session, faq, entity="calls")

    intro = await ai_service.generate_initial_response(
        faq=faq,
        original_message=session.original_message or "",
        session=session,
        context_note="You are about to show the user their recent calls.",
    )
    session.stage = ConversationStage.AWAITING_CALL_SELECTION
    return [
        _text(intro),
        ResponseItem(
            type=ResponseItemType.CALL_CARDS,
            data={"calls": calls, "prompt": "Please select the call you're referring to:"},
        ),
    ]


async def _handle_call_selection(session: SessionState, req: ChatRequest) -> List[ResponseItem]:
    if req.type != MessageInputType.SELECT_CALL:
        return [_text("Please tap on one of the calls above to continue.")]

    # Find call from the stored list (re-fetch would be wasteful; trust the id)
    selected_call = await _resolve_call(session, req.selected_id)
    if not selected_call:
        return [_text(
            "I couldn't find that call. Please select one of the calls shown above."
        )]

    session.selected_call = selected_call
    faq = faq_service.get_faq_by_id(session.matched_faq_id or "")
    if not faq:
        return [_error()]

    summary = _call_summary(selected_call)
    return await _respond_after_selection(session, faq, summary)


# ---------------------------------------------------------------------------
# PAYMENT flow
# ---------------------------------------------------------------------------

async def _start_payment_flow(session: SessionState, faq) -> List[ResponseItem]:
    if not session.auth_token and not DUMMY_MODE:
        return await _fallback_to_no_data(session, faq, entity="transactions")

    is_listener = session.user_type.value == "LISTENER"
    entity_label = "earnings" if is_listener else "transactions"

    try:
        if is_listener:
            transactions = await dostt_client.get_listener_earnings(
                session.auth_token, limit=5
            )
        else:
            transactions = await dostt_client.get_recent_transactions(
                session.auth_token, limit=5
            )
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            session.stage = ConversationStage.ENDED
            return [_text(
                "I wasn't able to verify your session. "
                "Please close this chat and reopen it from the Dostt app."
            )]
        return await _fallback_to_no_data(session, faq, entity=entity_label)
    except Exception:
        return await _fallback_to_no_data(session, faq, entity=entity_label)

    # Hide items that already have a ticket raised
    transactions = [t for t in transactions if not t.get("ticket_detail")]

    if not transactions:
        return await _fallback_to_no_data(session, faq, entity=entity_label)

    context_note = (
        "You are about to show the listener their recent earnings so they can pick the relevant one."
        if is_listener else
        "You are about to show the user their recent transactions so they can pick the relevant one."
    )
    prompt_text = (
        "Please select the earning you are referring to:"
        if is_listener else
        "Please select the transaction you're referring to:"
    )

    intro = await ai_service.generate_initial_response(
        faq=faq,
        original_message=session.original_message or "",
        session=session,
        context_note=context_note,
    )
    session.stage = ConversationStage.AWAITING_TRANSACTION_SELECTION
    return [
        _text(intro),
        ResponseItem(
            type=ResponseItemType.TRANSACTION_CARDS,
            data={"transactions": transactions, "prompt": prompt_text},
        ),
    ]


async def _start_payout_flow(session: SessionState, faq) -> List[ResponseItem]:
    if not session.auth_token and not DUMMY_MODE:
        return await _fallback_to_no_data(session, faq, entity="payouts")

    try:
        payouts = await dostt_client.get_listener_payouts(session.auth_token, limit=5)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            session.stage = ConversationStage.ENDED
            return [_text(
                "I wasn't able to verify your session. "
                "Please close this chat and reopen it from the Dostt app."
            )]
        return await _fallback_to_no_data(session, faq, entity="payouts")
    except Exception:
        return await _fallback_to_no_data(session, faq, entity="payouts")

    payouts = [p for p in payouts if not p.get("ticket_detail")]

    if not payouts:
        return await _fallback_to_no_data(session, faq, entity="payouts")

    intro = await ai_service.generate_initial_response(
        faq=faq,
        original_message=session.original_message or "",
        session=session,
        context_note="You are about to show the listener their recent withdrawals so they can pick the relevant one.",
    )
    session.stage = ConversationStage.AWAITING_TRANSACTION_SELECTION
    return [
        _text(intro),
        ResponseItem(
            type=ResponseItemType.TRANSACTION_CARDS,
            data={"transactions": payouts, "prompt": "Please select the withdrawal you are referring to:"},
        ),
    ]


async def _handle_transaction_selection(session: SessionState, req: ChatRequest) -> List[ResponseItem]:
    if req.type != MessageInputType.SELECT_TRANSACTION:
        return [_text("Please tap on one of the transactions above to continue.")]

    selected_tx = await _resolve_transaction(session, req.selected_id)
    if not selected_tx:
        return [_text(
            "I couldn't find that transaction. Please select one from the list above."
        )]

    session.selected_transaction = selected_tx
    faq = faq_service.get_faq_by_id(session.matched_faq_id or "")
    if not faq:
        return [_error()]

    summary = _transaction_summary(selected_tx)
    return await _respond_after_selection(session, faq, summary)


# ---------------------------------------------------------------------------
# OTHER flow
# ---------------------------------------------------------------------------

async def _handle_other_issue(session: SessionState, faq) -> List[ResponseItem]:
    answer_text = await ai_service.generate_initial_response(
        faq=faq,
        original_message=session.original_message or "",
        session=session,
    )
    items: List[ResponseItem] = [_text(answer_text)]

    if faq.feedback_type == FeedbackType.FEEDBACK_ONLY:
        session.stage = ConversationStage.ENDED
        items.append(_text("Hope that helps! If you have any other issue, feel free to ask."))

    elif faq.feedback_type in (FeedbackType.RAISE_COMPLAINT_ONLY, FeedbackType.BOTH):
        if _ticket_limit_reached(session):
            session.stage = ConversationStage.ENDED
            items.append(_ticket_limit_reply())
        else:
            session.stage = ConversationStage.ANSWERED
            items.append(_quick_replies_item())

    return items


# ---------------------------------------------------------------------------
# After call/transaction selection → apply feedback_type
# ---------------------------------------------------------------------------

async def _respond_after_selection(
    session: SessionState,
    faq,
    selection_summary: str,
) -> List[ResponseItem]:
    response_text = await ai_service.generate_post_selection_response(
        faq=faq,
        session=session,
        selection_summary=selection_summary,
    )
    items: List[ResponseItem] = [_text(response_text)]

    if faq.feedback_type == FeedbackType.FEEDBACK_ONLY:
        session.stage = ConversationStage.ENDED
        items.append(_text("Hope that helps! If you have any other issue, feel free to ask."))

    elif faq.feedback_type == FeedbackType.RAISE_COMPLAINT_ONLY:
        if _ticket_limit_reached(session):
            session.stage = ConversationStage.ENDED
            items.append(_ticket_limit_reply())
        else:
            session.stage = ConversationStage.AWAITING_TICKET_CONFIRMATION
            session.ticket_description = session.original_message
            items.append(_ticket_confirmation_item(session.ticket_description or "", faq.title11))

    elif faq.feedback_type == FeedbackType.BOTH:
        if _ticket_limit_reached(session):
            session.stage = ConversationStage.ENDED
            items.append(_ticket_limit_reply())
        else:
            session.stage = ConversationStage.ANSWERED
            items.append(_quick_replies_item())

    return items


# ---------------------------------------------------------------------------
# Ticket intent (ANSWERED stage)
# ---------------------------------------------------------------------------

async def _handle_ticket_intent(session: SessionState, req: ChatRequest) -> List[ResponseItem]:
    faq = faq_service.get_faq_by_id(session.matched_faq_id or "")

    # Quick-reply button pressed
    if req.type == MessageInputType.CONFIRM_TICKET:
        if _ticket_limit_reached(session):
            session.stage = ConversationStage.ENDED
            return [_ticket_limit_reply()]
        session.stage = ConversationStage.AWAITING_TICKET_CONFIRMATION
        session.ticket_description = session.original_message
        issue_name = faq.title11 if faq else "Support Request"
        return [_ticket_confirmation_item(session.ticket_description or "", issue_name)]

    if req.type == MessageInputType.CANCEL:
        session.stage = ConversationStage.ENDED
        return [_text("No problem! Is there anything else I can help you with?")]

    # Free-text fallback: classify intent
    wants_ticket = await ai_service.classify_ticket_intent(req.message or "")
    if wants_ticket:
        session.stage = ConversationStage.AWAITING_TICKET_CONFIRMATION
        session.ticket_description = session.original_message
        issue_name = faq.title11 if faq else "Support Request"
        return [_ticket_confirmation_item(session.ticket_description or "", issue_name)]

    session.stage = ConversationStage.ENDED
    return [_text("Alright, I'm glad I could help! Feel free to reach out if you need anything else.")]


# ---------------------------------------------------------------------------
# Ticket confirmation
# ---------------------------------------------------------------------------

async def _handle_ticket_confirmation(session: SessionState, req: ChatRequest) -> List[ResponseItem]:
    if req.type == MessageInputType.CANCEL:
        session.stage = ConversationStage.ENDED
        return [_text("Ticket creation cancelled. Is there anything else I can help you with?")]

    if req.type == MessageInputType.EDIT_TICKET:
        session.stage = ConversationStage.AWAITING_TICKET_EDIT
        return [_text(
            "Sure! Please type the description you'd like to use for this support ticket:"
        )]

    if req.type == MessageInputType.CONFIRM_TICKET:
        return _ask_call_consent(session)

    # Free-text fallback
    text_lower = (req.message or "").lower()
    if any(w in text_lower for w in ["yes", "confirm", "create", "ok", "sure", "proceed"]):
        return _ask_call_consent(session)
    if any(w in text_lower for w in ["no", "cancel", "stop", "don't"]):
        session.stage = ConversationStage.ENDED
        return [_text("Ticket creation cancelled. Is there anything else I can help you with?")]

    return [_text("Please use the buttons below to confirm, edit, or cancel the ticket.")]


async def _submit_ticket(session: SessionState) -> List[ResponseItem]:
    faq = faq_service.get_faq_by_id(session.matched_faq_id or "")
    if not faq:
        return [_error()]

    if not session.auth_token and not DUMMY_MODE:
        session.stage = ConversationStage.ENDED
        return [_text(
            "I wasn't able to submit the ticket because your session token is missing. "
            "Please try reopening the support chat from the app."
        )]

    reference_entity_id: Optional[str] = None
    reference_entity_type: Optional[str] = None

    if session.selected_call:
        raw_id = session.selected_call.get("id")
        if raw_id is not None:
            reference_entity_id = str(raw_id)
            reference_entity_type = "booking"  # user call or listener session

    elif session.selected_transaction:
        raw_id = session.selected_transaction.get("id")
        if raw_id is not None:
            reference_entity_id = str(raw_id)
            if faq.type == IssueType.PAYOUT:
                reference_entity_type = "dosttexpertpayout"
            elif session.user_type.value == "USER":
                reference_entity_type = "order"
            else:
                reference_entity_type = "booking"  # LISTENER earnings are booking-linked

    try:
        result = await dostt_client.create_support_ticket(
            token=session.auth_token,
            issue_id=str(faq.id),
            description=session.ticket_description or session.original_message or "",
            reference_entity_id=reference_entity_id,
            reference_entity_type=reference_entity_type,
            issue_type=int(faq.type),
            user_type=session.user_type.value,
            consent_call=bool(session.consent_call),
        )
        session.tickets_raised += 1
        session.stage = ConversationStage.TICKET_CREATED
        return [
            ResponseItem(
                type=ResponseItemType.TICKET_CREATED,
                data={"issue_name": faq.title11},
            ),
            _text(
                "You can track your ticket in the Raised Tickets section under Help & Support. "
                "Is there anything else I can help you with?"
            ),
        ]
    except httpx.HTTPStatusError as e:
        logger.error("Ticket creation HTTP error %s", e.response.status_code)
        session.stage = ConversationStage.ENDED
        return [_text(
            "I'm sorry, I wasn't able to create the ticket right now due to a server issue. "
            "Please try again later or contact us through the app's help section."
        )]
    except Exception as e:
        logger.error("Ticket creation error: %s", e)
        session.stage = ConversationStage.ENDED
        return [_text(
            "I'm sorry, I ran into an issue while creating your ticket. "
            "Please try again in a moment."
        )]


# ---------------------------------------------------------------------------
# Ticket edit
# ---------------------------------------------------------------------------

async def _handle_ticket_edit(session: SessionState, req: ChatRequest) -> List[ResponseItem]:
    if not req.message:
        return [_text("Please type the new ticket description you'd like to use.")]

    session.ticket_description = req.message
    session.stage = ConversationStage.AWAITING_TICKET_CONFIRMATION
    faq = faq_service.get_faq_by_id(session.matched_faq_id or "")
    issue_name = faq.title11 if faq else "Support Request"
    return [_ticket_confirmation_item(session.ticket_description, issue_name)]


# ---------------------------------------------------------------------------
# Call consent (chat-based, shown before ticket submission)
# ---------------------------------------------------------------------------

def _ask_call_consent(session: SessionState) -> List[ResponseItem]:
    session.stage = ConversationStage.AWAITING_CALL_CONSENT
    hour = (datetime.now(tz=timezone.utc) + _IST).hour
    if 9 <= hour < 19:
        question = "Would you like the Dostt team to call you to help resolve this?"
    else:
        question = (
            "Would you like the Dostt team to call you? "
            "Please note, by choosing Yes you agree that our support team "
            "may reach out to you until 1:00 AM IST."
        )
    return [
        _text(question),
        ResponseItem(
            type=ResponseItemType.QUICK_REPLIES,
            data={
                "options": [
                    {"id": "consent_yes", "label": "Yes, please call me"},
                    {"id": "consent_no", "label": "No thanks"},
                ]
            },
        ),
    ]


async def _handle_call_consent(session: SessionState, req: ChatRequest) -> List[ResponseItem]:
    if req.type == MessageInputType.CONSENT_YES:
        session.consent_call = True
        return await _submit_ticket(session)

    if req.type == MessageInputType.CONSENT_NO:
        session.consent_call = False
        return await _submit_ticket(session)

    # Free-text fallback
    msg = (req.message or "").lower()
    if any(w in msg for w in ["yes", "yeah", "sure", "ok", "please", "call"]):
        session.consent_call = True
        return await _submit_ticket(session)
    if any(w in msg for w in ["no", "nope", "skip", "don't"]):
        session.consent_call = False
        return await _submit_ticket(session)

    return [_text("Please tap 'Yes, please call me' or 'No thanks' to continue.")]


# ---------------------------------------------------------------------------
# Fallback: no call/transaction data
# ---------------------------------------------------------------------------

async def _fallback_to_no_data(session: SessionState, faq, entity: str) -> List[ResponseItem]:
    """
    When we cannot fetch calls/transactions, answer directly without selection.
    """
    answer_text = await ai_service.generate_initial_response(
        faq=faq,
        original_message=session.original_message or "",
        session=session,
        context_note=f"No {entity} data is available. Answer directly without asking for selection.",
    )
    items: List[ResponseItem] = [_text(answer_text)]

    if faq.feedback_type == FeedbackType.FEEDBACK_ONLY:
        session.stage = ConversationStage.ENDED
        items.append(_text("Hope that helps! If you have any other issue, feel free to ask."))

    elif faq.feedback_type in (FeedbackType.RAISE_COMPLAINT_ONLY, FeedbackType.BOTH):
        session.stage = ConversationStage.ANSWERED
        items.append(_quick_replies_item())

    return items


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _text(content: str) -> ResponseItem:
    return ResponseItem(type=ResponseItemType.TEXT, content=content)


def _error() -> ResponseItem:
    return ResponseItem(
        type=ResponseItemType.ERROR,
        content="Something went wrong. Please try again.",
    )


_IST = timedelta(hours=5, minutes=30)


def _ticket_confirmation_item(description: str, issue_name: str) -> ResponseItem:
    return ResponseItem(
        type=ResponseItemType.TICKET_CONFIRMATION,
        data={"description": description, "issue_name": issue_name},
    )


def _quick_replies_item() -> ResponseItem:
    return ResponseItem(
        type=ResponseItemType.QUICK_REPLIES,
        data={
            "options": [
                {"id": "confirm_ticket", "label": "Yes, I still have this issue"},
                {"id": "cancel", "label": "No, it's resolved"},
            ]
        },
    )


def _call_summary(call: Dict[str, Any]) -> str:
    expert = call.get("expert", {})
    name = expert.get("name", "listener") if isinstance(expert, dict) else "listener"
    date = call.get("booking_date", "")
    duration = call.get("total_duration", "")
    coins = call.get("coins", "")
    call_type = call.get("type", "")
    parts = [f"Call with {name}"]
    if date:
        parts.append(f"on {date}")
    if call_type:
        parts.append(f"({call_type})")
    if duration:
        parts.append(f"duration {duration}")
    if coins:
        parts.append(f"costing {coins} coins")
    return ", ".join(parts)


def _transaction_summary(tx: Dict[str, Any]) -> str:
    tx_type = tx.get("type", "transaction")
    coins = tx.get("coins", "")
    amount = tx.get("amount", "")
    status = tx.get("status", "")
    parts = [tx_type.replace("_", " ").title()]
    if coins:
        parts.append(f"of {coins} coins")
    if amount:
        parts.append(f"(₹{amount})")
    if status:
        parts.append(f"— {status}")
    return " ".join(parts)


async def _resolve_call(session: SessionState, call_id: Optional[str]) -> Optional[Dict[str, Any]]:
    """Try to find the call from a fresh API fetch."""
    if not call_id:
        return None
    if not session.auth_token and not DUMMY_MODE:
        return None
    try:
        if session.user_type.value == "LISTENER":
            calls = await dostt_client.get_recent_listener_sessions(session.auth_token, limit=5)
        else:
            calls = await dostt_client.get_recent_calls(session.auth_token, limit=5)
        return next((c for c in calls if str(c.get("id")) == str(call_id)), None)
    except Exception:
        return {"id": call_id}


async def _resolve_transaction(session: SessionState, tx_id: Optional[str]) -> Optional[Dict[str, Any]]:
    if not tx_id:
        return None
    if not session.auth_token and not DUMMY_MODE:
        return None
    try:
        faq = faq_service.get_faq_by_id(session.matched_faq_id or "")
        if faq and faq.type == IssueType.PAYOUT:
            items = await dostt_client.get_listener_payouts(session.auth_token, limit=5)
        elif session.user_type.value == "LISTENER":
            items = await dostt_client.get_listener_earnings(session.auth_token, limit=5)
        else:
            items = await dostt_client.get_recent_transactions(session.auth_token, limit=5)
        found = next((t for t in items if str(t.get("id")) == str(tx_id)), None)
        return found or {"id": tx_id}
    except Exception:
        return {"id": tx_id}


def _find_by_id(item_id: Optional[str], session: SessionState, key: str) -> Optional[Dict[str, Any]]:
    """Placeholder for client-side selected item lookup."""
    return None


def _ticket_limit_reached(session: SessionState) -> bool:
    return session.tickets_raised >= MAX_TICKETS_PER_SESSION


def _ticket_limit_reply() -> ResponseItem:
    return _text(
        f"You can raise up to {MAX_TICKETS_PER_SESSION} tickets per chat session, "
        f"and you have already used all {MAX_TICKETS_PER_SESSION}. "
        "To raise more, please open a new support chat. "
        "You can track your existing tickets in the Raised Tickets section under Help & Support."
    )


def _out_of_scope_reply() -> str:
    return (
        "I'm here to help with Dostt app support queries only. "
        "Feel free to ask me anything about your calls, payments, account, or any other issue!"
    )
