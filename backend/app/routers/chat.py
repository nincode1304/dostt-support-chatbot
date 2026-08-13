"""
Chat router: orchestrates the guided conversation state machine.

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
from app.services.translations import t
from app.services.faq_service import get_faq_title

router = APIRouter(prefix="/api", tags=["chat"])
logger = logging.getLogger(__name__)

MAX_TICKETS_PER_SESSION = 2


# ---------------------------------------------------------------------------
# Session init
# ---------------------------------------------------------------------------

_ALLOWED_LANGUAGES = frozenset({
    "English", "Hindi", "Tamil", "Telugu", "Malayalam",
    "Kannada", "Marathi", "Punjabi", "Bengali", "Gujarati", "Odia",
})


@router.post("/session/init", response_model=InitSessionResponse)
async def init_session(req: InitSessionRequest) -> InitSessionResponse:
    language = req.language if req.language in _ALLOWED_LANGUAGES else "English"
    token_hint = f"{req.auth_token[:6]}…" if req.auth_token and len(req.auth_token) > 6 else "[empty]"
    logger.info(
        "Session init → user_type=%s language=%s platform=%s app_version_code=%s token=%s",
        req.user_type, language, req.platform, req.app_version_code, token_hint,
    )
    session = session_service.create_session(
        auth_token=req.auth_token,
        user_type=req.user_type,
        language=language,
        platform=req.platform or "Android",
        app_version_code=req.app_version_code or "131",
    )
    return InitSessionResponse(
        session_id=session.session_id,
        greeting=t(language, "greeting"),
        items=_category_cards_items(language),
    )


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

    if req.type == MessageInputType.TEXT and req.message:
        session.messages.append(ChatMessage(role="user", content=req.message))

    try:
        items = await _dispatch(session, req)
    except Exception as e:
        logger.exception("Unhandled error in chat dispatch: %s", e)
        items = [ResponseItem(
            type=ResponseItemType.ERROR,
            content=t(session.language, "unhandled_error"),
        )]

    for item in items:
        if item.type == ResponseItemType.TEXT and item.content:
            session.messages.append(ChatMessage(role="assistant", content=item.content))

    session_service.save_session(session)
    return ChatResponse(session_id=session.session_id, items=items)


# ---------------------------------------------------------------------------
# Stage dispatcher
# ---------------------------------------------------------------------------

async def _dispatch(session: SessionState, req: ChatRequest) -> List[ResponseItem]:
    # Language switch
    if req.type == MessageInputType.SET_LANGUAGE:
        if req.language and req.language in _ALLOWED_LANGUAGES:
            session.language = req.language
        _reset_for_new_issue(session)
        return [_text(t(session.language, "greeting")), *_category_cards_items(session.language)]

    stage = session.stage

    if stage in (ConversationStage.INITIAL, ConversationStage.AWAITING_CATEGORY_SELECTION):
        return await _handle_category_selection(session, req)

    if stage == ConversationStage.AWAITING_TRANSACTION_SUBTYPE:
        return await _handle_transaction_subtype(session, req)

    if stage == ConversationStage.AWAITING_CALL_SELECTION:
        return await _handle_call_selection(session, req)

    if stage == ConversationStage.AWAITING_TRANSACTION_SELECTION:
        return await _handle_transaction_selection(session, req)

    if stage == ConversationStage.AWAITING_FAQ_SELECTION:
        return await _handle_faq_selection(session, req)

    if stage == ConversationStage.AWAITING_OTHER_TEXT:
        return await _handle_other_text(session, req)

    if stage == ConversationStage.AWAITING_MORE_HELP_RESPONSE:
        return await _handle_more_help_response(session, req)

    if stage == ConversationStage.ANSWERED:
        return await _handle_ticket_intent(session, req)

    if stage == ConversationStage.AWAITING_TICKET_CONFIRMATION:
        return await _handle_ticket_confirmation(session, req)

    if stage == ConversationStage.AWAITING_TICKET_EDIT:
        return await _handle_ticket_edit(session, req)

    if stage == ConversationStage.AWAITING_CALL_CONSENT:
        return await _handle_call_consent(session, req)

    # TICKET_CREATED or ENDED — reset and show category cards
    _reset_for_new_issue(session)
    return _category_cards_items(session.language)


# ---------------------------------------------------------------------------
# Category selection
# ---------------------------------------------------------------------------

async def _handle_category_selection(session: SessionState, req: ChatRequest) -> List[ResponseItem]:
    if req.type != MessageInputType.SELECT_CATEGORY:
        return _category_cards_items(session.language)

    category = req.selected_id
    session.selected_category = category

    if category == "calls":
        return await _start_call_category_flow(session)
    if category == "transactions":
        return await _start_transaction_category_flow(session)
    if category == "other":
        session.stage = ConversationStage.AWAITING_OTHER_TEXT
        return [_text(t(session.language, "other_prompt"))]

    return _category_cards_items(session.language)


# ---------------------------------------------------------------------------
# CALL category flow
# ---------------------------------------------------------------------------

async def _start_call_category_flow(session: SessionState) -> List[ResponseItem]:
    lang = session.language
    if not session.auth_token and not DUMMY_MODE:
        return _show_faq_cards(session)

    try:
        if session.user_type.value == "LISTENER":
            calls = await dostt_client.get_recent_listener_sessions(session.auth_token, limit=20, platform=session.platform, app_version_code=session.app_version_code)
        else:
            calls = await dostt_client.get_recent_calls(session.auth_token, limit=20, platform=session.platform, app_version_code=session.app_version_code)
        calls = [c for c in calls if not c.get("ticket_detail")][:5]
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            session.stage = ConversationStage.ENDED
            return [_text(t(lang, "session_error"))]
        calls = []
    except Exception:
        calls = []

    if not calls:
        return _no_recent_activity(session)

    session.stage = ConversationStage.AWAITING_CALL_SELECTION
    return [
        _text(t(lang, "select_call_prompt")),
        ResponseItem(
            type=ResponseItemType.CALL_CARDS,
            data={"calls": calls, "prompt": t(lang, "select_call_cards_prompt")},
        ),
    ]


async def _handle_call_selection(session: SessionState, req: ChatRequest) -> List[ResponseItem]:
    lang = session.language
    if req.type != MessageInputType.SELECT_CALL:
        return [_text(t(lang, "tap_call_above"))]

    selected_call = await _resolve_call(session, req.selected_id)
    if not selected_call:
        return [_text(t(lang, "call_not_found"))]

    session.selected_call = selected_call

    if session.preselected_faq_id:
        faq = faq_service.get_faq_by_id(session.preselected_faq_id)
        session.preselected_faq_id = None
        if faq:
            return await _respond_after_selection(session, faq, _call_summary(selected_call))

    return _show_faq_cards(session)


# ---------------------------------------------------------------------------
# TRANSACTION category flow
# ---------------------------------------------------------------------------

async def _start_transaction_category_flow(session: SessionState) -> List[ResponseItem]:
    lang = session.language
    if session.user_type.value == "LISTENER":
        session.stage = ConversationStage.AWAITING_TRANSACTION_SUBTYPE
        return [
            _text(t(lang, "transaction_subtype_prompt")),
            ResponseItem(
                type=ResponseItemType.TRANSACTION_SUBTYPE_CARDS,
                data={
                    "options": [
                        {"id": "earnings", "label": t(lang, "subtype_earnings")},
                        {"id": "payouts", "label": t(lang, "subtype_payouts")},
                    ]
                },
            ),
        ]
    return await _start_user_transaction_flow(session)


async def _handle_transaction_subtype(session: SessionState, req: ChatRequest) -> List[ResponseItem]:
    lang = session.language
    if req.type != MessageInputType.SELECT_TRANSACTION_SUBTYPE:
        return [_text(t(lang, "select_option_above"))]

    subtype = req.selected_id
    session.selected_transaction_subtype = subtype

    if subtype == "payouts":
        return await _start_payout_flow(session)
    return await _start_earnings_flow(session)


async def _start_user_transaction_flow(session: SessionState) -> List[ResponseItem]:
    lang = session.language
    if not session.auth_token and not DUMMY_MODE:
        return _show_faq_cards(session)

    try:
        transactions = await dostt_client.get_recent_transactions(session.auth_token, limit=20, platform=session.platform, app_version_code=session.app_version_code)
        transactions = [tx for tx in transactions if not tx.get("ticket_detail") and tx.get("title") == "Wallet Recharge"][:5]
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            session.stage = ConversationStage.ENDED
            return [_text(t(lang, "session_error"))]
        transactions = []
    except Exception:
        transactions = []

    if not transactions:
        return _no_recent_activity(session)

    session.stage = ConversationStage.AWAITING_TRANSACTION_SELECTION
    return [
        _text(t(lang, "select_tx_prompt")),
        ResponseItem(
            type=ResponseItemType.TRANSACTION_CARDS,
            data={"transactions": transactions, "prompt": t(lang, "select_tx_cards_prompt")},
        ),
    ]


async def _start_earnings_flow(session: SessionState) -> List[ResponseItem]:
    lang = session.language
    if not session.auth_token and not DUMMY_MODE:
        return _show_faq_cards(session)

    try:
        transactions = await dostt_client.get_listener_earnings(session.auth_token, limit=20, platform=session.platform, app_version_code=session.app_version_code)
        transactions = [tx for tx in transactions if not tx.get("ticket_detail")][:5]
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            session.stage = ConversationStage.ENDED
            return [_text(t(lang, "session_error"))]
        transactions = []
    except Exception:
        transactions = []

    if not transactions:
        return _no_recent_activity(session)

    session.stage = ConversationStage.AWAITING_TRANSACTION_SELECTION
    return [
        _text(t(lang, "select_earning_prompt")),
        ResponseItem(
            type=ResponseItemType.TRANSACTION_CARDS,
            data={"transactions": transactions, "prompt": t(lang, "select_earning_cards_prompt")},
        ),
    ]


async def _start_payout_flow(session: SessionState) -> List[ResponseItem]:
    lang = session.language
    if not session.auth_token and not DUMMY_MODE:
        return _show_faq_cards(session)

    try:
        payouts = await dostt_client.get_listener_payouts(session.auth_token, limit=20, platform=session.platform, app_version_code=session.app_version_code)
        payouts = [p for p in payouts if not p.get("ticket_detail")][:5]
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            session.stage = ConversationStage.ENDED
            return [_text(t(lang, "session_error"))]
        payouts = []
    except Exception:
        payouts = []

    if not payouts:
        return _no_recent_activity(session)

    session.stage = ConversationStage.AWAITING_TRANSACTION_SELECTION
    return [
        _text(t(lang, "select_withdrawal_prompt")),
        ResponseItem(
            type=ResponseItemType.TRANSACTION_CARDS,
            data={"transactions": payouts, "prompt": t(lang, "select_withdrawal_cards_prompt")},
        ),
    ]


async def _handle_transaction_selection(session: SessionState, req: ChatRequest) -> List[ResponseItem]:
    lang = session.language
    if req.type != MessageInputType.SELECT_TRANSACTION:
        return [_text(t(lang, "tap_tx_above"))]

    selected_tx = await _resolve_transaction(session, req.selected_id)
    if not selected_tx:
        return [_text(t(lang, "tx_not_found"))]

    session.selected_transaction = selected_tx

    if session.preselected_faq_id:
        faq = faq_service.get_faq_by_id(session.preselected_faq_id)
        session.preselected_faq_id = None
        if faq:
            return await _respond_after_selection(session, faq, _transaction_summary(selected_tx))

    return _show_faq_cards(session)


# ---------------------------------------------------------------------------
# FAQ selection
# ---------------------------------------------------------------------------

def _show_faq_cards(session: SessionState) -> List[ResponseItem]:
    lang = session.language
    category = session.selected_category
    subtype = session.selected_transaction_subtype
    user_type = session.user_type.value

    if category == "calls":
        faqs = faq_service.get_faqs_by_issue_type_and_user_type(IssueType.CALL, user_type)
    elif category == "transactions":
        if user_type == "LISTENER":
            if subtype == "payouts":
                faqs = faq_service.get_listener_payout_faqs()
            else:
                faqs = faq_service.get_listener_earnings_faqs()
        else:
            faqs = faq_service.get_faqs_by_issue_type_and_user_type(IssueType.PAYMENT, user_type)
    else:
        faqs = faq_service.get_faqs_by_issue_type_and_user_type(IssueType.OTHER, user_type)

    session.stage = ConversationStage.AWAITING_FAQ_SELECTION
    return [
        _text(t(lang, "what_issue")),
        ResponseItem(
            type=ResponseItemType.FAQ_CARDS,
            data={"faqs": [{"id": str(f.id), "title": get_faq_title(str(f.id), lang, f.title11)} for f in faqs]},
        ),
    ]


async def _handle_faq_selection(session: SessionState, req: ChatRequest) -> List[ResponseItem]:
    lang = session.language
    if req.type != MessageInputType.SELECT_FAQ:
        return [_text(t(lang, "select_faq_above"))]

    faq = faq_service.get_faq_by_id(req.selected_id or "")
    if not faq:
        return [_error(lang)]

    session.matched_faq_id = str(faq.id)
    session.original_message = faq.title11

    if session.selected_call:
        return await _respond_after_selection(session, faq, _call_summary(session.selected_call))

    if session.selected_transaction:
        return await _respond_after_selection(session, faq, _transaction_summary(session.selected_transaction))

    # No entity selected (no data available) — answer directly
    if faq_service.is_payout_faq(faq.id):
        return await _fallback_to_no_data(session, faq, entity="payouts")
    if faq.type == IssueType.CALL:
        return await _fallback_to_no_data(session, faq, entity="calls")
    if faq.type == IssueType.PAYMENT:
        return await _fallback_to_no_data(session, faq, entity="transactions")
    return await _handle_other_issue(session, faq)


# ---------------------------------------------------------------------------
# OTHER category: free-text → AI match → answer
# ---------------------------------------------------------------------------

_CONTENT_KEY_MAP: Dict[str, str] = {
    "MENTAL_HEALTH":   "content_mental_health",
    "ABUSE_SAFETY":    "content_domestic_abuse",
    "MINOR_USER":      "content_minor_user",
    "HARMFUL":         "content_harmful",
    "VERBAL_ABUSE":    "content_verbal_abuse",
    "PRIVACY_PROBING": "content_privacy",
    "PROMPT_INJECTION":"content_injection",
    "SPAM_GIBBERISH":  "content_gibberish",
    "OFF_TOPIC":       "content_off_topic",
    "LEGAL_THREAT":    "content_legal",
    "CALL_REQUEST":    "content_call_request",
    "SCAM_FRAUD":      "content_scam",
    "MISINFORMATION":  "content_misinformation",
}


async def _handle_other_text(session: SessionState, req: ChatRequest) -> List[ResponseItem]:
    lang = session.language
    if not req.message:
        return [_text(t(lang, "other_prompt"))]

    # Single Gemini call: classify intent AND identify FAQ in one pass
    all_faqs = faq_service.get_faqs_for_user_type(session.user_type.value)
    result = await ai_service.identify_other_intent(req.message, session.user_type.value, all_faqs)
    intent = result.get("intent", "UNKNOWN")

    if intent == "SPECIAL":
        translation_key = _CONTENT_KEY_MAP.get(result.get("category", ""))
        if translation_key:
            return [_text(t(lang, translation_key))]
        intent = "UNKNOWN"

    if intent == "FAQ":
        raw_id = result.get("faq_id")
        faq = faq_service.get_faq_by_id(str(int(raw_id))) if raw_id is not None else None
        if faq:
            session.matched_faq_id = str(faq.id)
            session.original_message = req.message

            if faq.type == IssueType.CALL:
                session.selected_category = "calls"
                session.preselected_faq_id = str(faq.id)
                return await _start_call_category_flow(session)

            if faq.type == IssueType.PAYMENT:
                session.selected_category = "transactions"
                session.preselected_faq_id = str(faq.id)
                if session.user_type.value == "LISTENER":
                    if faq_service.is_payout_faq(faq.id):
                        session.selected_transaction_subtype = "payouts"
                        return await _start_payout_flow(session)
                    else:
                        session.selected_transaction_subtype = "earnings"
                        return await _start_earnings_flow(session)
                return await _start_user_transaction_flow(session)

            return await _handle_other_issue(session, faq)
        intent = "UNKNOWN"

    # UNKNOWN — app-related but no specific FAQ matched.
    # Open a generic "other issues" ticket using FAQ 397 so the user is never
    # left without a path to resolution.
    faq_fallback = faq_service.get_faq_by_id("397")
    if faq_fallback:
        session.matched_faq_id = "397"
        session.original_message = req.message
        return await _handle_other_issue(session, faq_fallback)
    return [_text(t(lang, "cannot_identify")), *_ask_more_help(session)]


# ---------------------------------------------------------------------------
# OTHER issue handler (direct answer)
# ---------------------------------------------------------------------------

async def _handle_other_issue(session: SessionState, faq) -> List[ResponseItem]:
    lang = session.language
    answer_text = await ai_service.generate_initial_response(
        faq=faq,
        original_message=session.original_message or "",
        session=session,
    )
    items: List[ResponseItem] = [_text(answer_text)]

    if faq.feedback_type == FeedbackType.FEEDBACK_ONLY:
        items.extend(_ask_more_help(session))

    elif faq.feedback_type == FeedbackType.RAISE_COMPLAINT_ONLY:
        if _ticket_limit_reached(session):
            items.append(_ticket_limit_reply(lang))
            items.extend(_ask_more_help(session))
        else:
            session.stage = ConversationStage.ANSWERED
            items.append(_text(t(lang, "raise_ticket_prompt")))
            items.append(_quick_replies_item(lang))

    elif faq.feedback_type == FeedbackType.BOTH:
        if _ticket_limit_reached(session):
            items.append(_ticket_limit_reply(lang))
            items.extend(_ask_more_help(session))
        else:
            session.stage = ConversationStage.ANSWERED
            items.append(_text(t(lang, "still_facing")))
            items.append(_quick_replies_item(lang))

    return items


# ---------------------------------------------------------------------------
# After call/transaction selection → apply feedback_type
# ---------------------------------------------------------------------------

async def _respond_after_selection(
    session: SessionState,
    faq,
    selection_summary: str,
) -> List[ResponseItem]:
    lang = session.language
    response_text = await ai_service.generate_post_selection_response(
        faq=faq,
        session=session,
        selection_summary=selection_summary,
    )
    items: List[ResponseItem] = [_text(response_text)]

    if faq.feedback_type == FeedbackType.FEEDBACK_ONLY:
        items.extend(_ask_more_help(session))

    elif faq.feedback_type == FeedbackType.RAISE_COMPLAINT_ONLY:
        if _ticket_limit_reached(session):
            items.append(_ticket_limit_reply(lang))
            items.extend(_ask_more_help(session))
        else:
            session.stage = ConversationStage.AWAITING_TICKET_CONFIRMATION
            session.ticket_description = session.original_message
            items.append(_ticket_confirmation_item(session.ticket_description or "", get_faq_title(str(faq.id), lang, faq.title11)))

    elif faq.feedback_type == FeedbackType.BOTH:
        if _ticket_limit_reached(session):
            items.append(_ticket_limit_reply(lang))
            items.extend(_ask_more_help(session))
        else:
            session.stage = ConversationStage.ANSWERED
            items.append(_text(t(lang, "still_facing")))
            items.append(_quick_replies_item(lang))

    return items


# ---------------------------------------------------------------------------
# Ticket intent (ANSWERED stage)
# ---------------------------------------------------------------------------

async def _handle_ticket_intent(session: SessionState, req: ChatRequest) -> List[ResponseItem]:
    lang = session.language
    faq = faq_service.get_faq_by_id(session.matched_faq_id or "")

    if req.type == MessageInputType.CONFIRM_TICKET:
        if _ticket_limit_reached(session):
            items = [_ticket_limit_reply(lang)]
            _reset_for_new_issue(session)
            items.extend(_category_cards_items(lang))
            return items
        session.stage = ConversationStage.AWAITING_TICKET_CONFIRMATION
        session.ticket_description = session.original_message
        issue_name = get_faq_title(str(faq.id), lang, faq.title11) if faq else "Support Request"
        return [_ticket_confirmation_item(session.ticket_description or "", issue_name)]

    if req.type == MessageInputType.CANCEL:
        return [_text(t(lang, "no_problem")), *_ask_more_help(session)]

    # Free-text fallback
    wants_ticket = await ai_service.classify_ticket_intent(req.message or "")
    if wants_ticket:
        if _ticket_limit_reached(session):
            items = [_ticket_limit_reply(lang)]
            items.extend(_ask_more_help(session))
            return items
        session.stage = ConversationStage.AWAITING_TICKET_CONFIRMATION
        session.ticket_description = session.original_message
        issue_name = get_faq_title(str(faq.id), lang, faq.title11) if faq else "Support Request"
        return [_ticket_confirmation_item(session.ticket_description or "", issue_name)]

    return [_text(t(lang, "glad_helped")), *_ask_more_help(session)]


# ---------------------------------------------------------------------------
# Ticket confirmation
# ---------------------------------------------------------------------------

async def _handle_ticket_confirmation(session: SessionState, req: ChatRequest) -> List[ResponseItem]:
    lang = session.language
    if req.type == MessageInputType.CANCEL:
        return [_text(t(lang, "ticket_cancelled")), *_ask_more_help(session)]

    if req.type == MessageInputType.EDIT_TICKET:
        session.stage = ConversationStage.AWAITING_TICKET_EDIT
        return [_text(t(lang, "edit_ticket_prompt"))]

    if req.type == MessageInputType.CONFIRM_TICKET:
        return _ask_call_consent(session)

    text_lower = (req.message or "").lower()
    if any(w in text_lower for w in ["yes", "confirm", "create", "ok", "sure", "proceed"]):
        return _ask_call_consent(session)
    if any(w in text_lower for w in ["no", "cancel", "stop", "don't"]):
        return [_text(t(lang, "ticket_cancelled")), *_ask_more_help(session)]

    return [_text(t(lang, "confirm_edit_cancel"))]


async def _submit_ticket(session: SessionState) -> List[ResponseItem]:
    lang = session.language
    faq = faq_service.get_faq_by_id(session.matched_faq_id or "")
    if not faq:
        return [_error(lang)]

    if not session.auth_token and not DUMMY_MODE:
        _reset_for_new_issue(session)
        return [_text(t(lang, "ticket_no_token"))]

    reference_entity_id: Optional[str] = None
    reference_entity_type: Optional[str] = None

    if session.selected_call:
        raw_id = session.selected_call.get("id")
        if raw_id is not None:
            reference_entity_id = str(raw_id)
            reference_entity_type = "booking"

    elif session.selected_transaction:
        raw_id = session.selected_transaction.get("id")
        if raw_id is not None:
            reference_entity_id = str(raw_id)
            if faq_service.is_payout_faq(faq.id):
                reference_entity_type = "dosttexpertpayout"
            elif session.user_type.value == "USER":
                reference_entity_type = "order"
            else:
                reference_entity_type = "booking"

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
            platform=session.platform,
            app_version_code=session.app_version_code,
        )
        session.tickets_raised += 1
        issue_name = get_faq_title(str(faq.id), lang, faq.title11)
        ticket_id = result.get("ticket_id") if isinstance(result, dict) else None
        return [
            ResponseItem(
                type=ResponseItemType.TICKET_CREATED,
                data={
                    "issue_name": issue_name,
                    "title": t(lang, "ticket_created_title"),
                    "hint": t(lang, "ticket_track_hint"),
                    **({"ticket_id": ticket_id} if ticket_id else {}),
                },
            ),
            _text(t(lang, "ticket_track")),
            *_ask_more_help(session),
        ]
    except httpx.HTTPStatusError as e:
        logger.error("Ticket creation HTTP error %s: %s", e.response.status_code, e.response.text)
        try:
            body = e.response.json()
            raw = body.get("message") or body.get("detail") or body.get("error") or e.response.text
            if isinstance(raw, dict):
                parts = []
                for v in raw.values():
                    parts += v if isinstance(v, list) else [str(v)]
                user_msg = " ".join(parts)
            else:
                user_msg = str(raw)
        except Exception:
            user_msg = e.response.text or t(lang, "ticket_api_error")
        session.stage = ConversationStage.ENDED
        return [_text(user_msg)]
    except Exception as e:
        logger.error("Ticket creation error: %s", e)
        session.stage = ConversationStage.ENDED
        return [_text(t(lang, "ticket_error"))]


# ---------------------------------------------------------------------------
# Ticket edit
# ---------------------------------------------------------------------------

async def _handle_ticket_edit(session: SessionState, req: ChatRequest) -> List[ResponseItem]:
    lang = session.language
    if req.type == MessageInputType.CANCEL:
        _reset_for_new_issue(session)
        return [_text(t(lang, "ticket_cancelled")), *_ask_more_help(session)]
    if not req.message:
        return [_text(t(lang, "edit_ticket_prompt"))]

    session.ticket_description = req.message
    session.stage = ConversationStage.AWAITING_TICKET_CONFIRMATION
    faq = faq_service.get_faq_by_id(session.matched_faq_id or "")
    issue_name = get_faq_title(str(faq.id), lang, faq.title11) if faq else "Support Request"
    return [_ticket_confirmation_item(session.ticket_description, issue_name)]


# ---------------------------------------------------------------------------
# Call consent
# ---------------------------------------------------------------------------

def _ask_call_consent(session: SessionState) -> List[ResponseItem]:
    lang = session.language
    session.stage = ConversationStage.AWAITING_CALL_CONSENT
    hour = (datetime.now(tz=timezone.utc) + _IST).hour
    off_hours = hour < 9 or hour >= 19
    quick_reply_data: Dict[str, Any] = {
        "options": [
            {"id": "consent_yes", "label": t(lang, "consent_yes")},
            {"id": "consent_no", "label": t(lang, "consent_no")},
        ]
    }
    if off_hours:
        quick_reply_data["disclaimer"] = t(lang, "off_hours_disclaimer")
    return [
        _text(t(lang, "consent_question")),
        ResponseItem(type=ResponseItemType.QUICK_REPLIES, data=quick_reply_data),
    ]


async def _handle_call_consent(session: SessionState, req: ChatRequest) -> List[ResponseItem]:
    lang = session.language
    if req.type == MessageInputType.CONSENT_YES:
        session.consent_call = True
        return await _submit_ticket(session)

    if req.type == MessageInputType.CONSENT_NO:
        session.consent_call = False
        return await _submit_ticket(session)

    msg = (req.message or "").lower()
    if any(w in msg for w in ["yes", "yeah", "sure", "ok", "please", "call"]):
        session.consent_call = True
        return await _submit_ticket(session)
    if any(w in msg for w in ["no", "nope", "skip", "don't"]):
        session.consent_call = False
        return await _submit_ticket(session)

    return [_text(t(lang, "consent_prompt"))]


# ---------------------------------------------------------------------------
# Fallback: no call/transaction data available
# ---------------------------------------------------------------------------

async def _fallback_to_no_data(session: SessionState, faq, entity: str) -> List[ResponseItem]:
    lang = session.language
    answer_text = await ai_service.generate_initial_response(
        faq=faq,
        original_message=session.original_message or "",
        session=session,
        context_note=f"No {entity} data is available. Answer directly without asking for selection.",
    )
    items: List[ResponseItem] = [_text(answer_text)]

    if faq.feedback_type == FeedbackType.FEEDBACK_ONLY:
        items.extend(_ask_more_help(session))

    elif faq.feedback_type == FeedbackType.RAISE_COMPLAINT_ONLY:
        if _ticket_limit_reached(session):
            items.append(_ticket_limit_reply(lang))
            items.extend(_ask_more_help(session))
        else:
            session.stage = ConversationStage.ANSWERED
            items.append(_text(t(lang, "raise_ticket_prompt")))
            items.append(_quick_replies_item(lang))

    elif faq.feedback_type == FeedbackType.BOTH:
        if _ticket_limit_reached(session):
            items.append(_ticket_limit_reply(lang))
            items.extend(_ask_more_help(session))
        else:
            session.stage = ConversationStage.ANSWERED
            items.append(_text(t(lang, "still_facing")))
            items.append(_quick_replies_item(lang))

    return items


# ---------------------------------------------------------------------------
# No recent activity
# ---------------------------------------------------------------------------

def _no_recent_activity(session: SessionState) -> List[ResponseItem]:
    return [_text(t(session.language, "no_recent_activity")), *_ask_more_help(session)]


# ---------------------------------------------------------------------------
# More help prompt
# ---------------------------------------------------------------------------

def _ask_more_help(session: SessionState) -> List[ResponseItem]:
    lang = session.language
    _reset_for_new_issue(session)
    session.stage = ConversationStage.AWAITING_MORE_HELP_RESPONSE
    return [
        _text(t(lang, "more_help")),
        ResponseItem(
            type=ResponseItemType.QUICK_REPLIES,
            data={
                "options": [
                    {"id": "more_help_yes", "label": t(lang, "more_help_yes")},
                    {"id": "more_help_no", "label": t(lang, "more_help_no")},
                ]
            },
        ),
    ]


async def _handle_more_help_response(session: SessionState, req: ChatRequest) -> List[ResponseItem]:
    lang = session.language
    if req.type == MessageInputType.MORE_HELP_YES:
        _reset_for_new_issue(session)
        return [_text(t(lang, "sure_what_help")), *_category_cards_items(lang)]

    if req.type == MessageInputType.MORE_HELP_NO:
        session.stage = ConversationStage.ENDED
        return [ResponseItem(
            type=ResponseItemType.CHAT_ENDED,
            content=t(lang, "chat_ended"),
        )]

    return [_text(t(lang, "select_option_above"))]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _text(content: str) -> ResponseItem:
    return ResponseItem(type=ResponseItemType.TEXT, content=content)


def _error(lang: str = "English") -> ResponseItem:
    return ResponseItem(
        type=ResponseItemType.ERROR,
        content=t(lang, "generic_error"),
    )


_IST = timedelta(hours=5, minutes=30)


def _ticket_confirmation_item(description: str, issue_name: str) -> ResponseItem:
    return ResponseItem(
        type=ResponseItemType.TICKET_CONFIRMATION,
        data={"description": description, "issue_name": issue_name},
    )


def _quick_replies_item(lang: str) -> ResponseItem:
    return ResponseItem(
        type=ResponseItemType.QUICK_REPLIES,
        data={
            "options": [
                {"id": "confirm_ticket", "label": t(lang, "yes_still_issue")},
                {"id": "cancel", "label": t(lang, "no_resolved")},
            ]
        },
    )


def _category_cards_items(lang: str) -> List[ResponseItem]:
    return [
        ResponseItem(
            type=ResponseItemType.CATEGORY_CARDS,
            data={
                "options": [
                    {"id": "calls", "label": t(lang, "category_calls"), "icon": "phone"},
                    {"id": "transactions", "label": t(lang, "category_transactions"), "icon": "wallet"},
                    {"id": "other", "label": t(lang, "category_other"), "icon": "chat"},
                ]
            },
        )
    ]


def _reset_for_new_issue(session: SessionState) -> None:
    session.matched_faq_id = None
    session.original_message = None
    session.selected_call = None
    session.selected_transaction = None
    session.ticket_description = None
    session.consent_call = None
    session.selected_category = None
    session.selected_transaction_subtype = None
    session.preselected_faq_id = None
    session.other_retry_count = 0
    session.stage = ConversationStage.AWAITING_CATEGORY_SELECTION


def _ticket_limit_reached(session: SessionState) -> bool:
    return session.tickets_raised >= MAX_TICKETS_PER_SESSION


def _ticket_limit_reply(lang: str) -> ResponseItem:
    return _text(t(lang, "ticket_limit", max=MAX_TICKETS_PER_SESSION))


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
    if not call_id:
        return None
    if not session.auth_token and not DUMMY_MODE:
        return None
    try:
        if session.user_type.value == "LISTENER":
            calls = await dostt_client.get_recent_listener_sessions(session.auth_token, limit=20, platform=session.platform, app_version_code=session.app_version_code)
        else:
            calls = await dostt_client.get_recent_calls(session.auth_token, limit=20, platform=session.platform, app_version_code=session.app_version_code)
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
        is_payout = (faq_service.is_payout_faq(faq.id) if faq else False) or session.selected_transaction_subtype == "payouts"
        if is_payout:
            items = await dostt_client.get_listener_payouts(session.auth_token, limit=20, platform=session.platform, app_version_code=session.app_version_code)
        elif session.user_type.value == "LISTENER":
            items = await dostt_client.get_listener_earnings(session.auth_token, limit=20, platform=session.platform, app_version_code=session.app_version_code)
        else:
            items = await dostt_client.get_recent_transactions(session.auth_token, limit=20, platform=session.platform, app_version_code=session.app_version_code)
        found = next((tx for tx in items if str(tx.get("id")) == str(tx_id)), None)
        return found or {"id": tx_id}
    except Exception:
        return {"id": tx_id}
