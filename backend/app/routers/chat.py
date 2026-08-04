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

router = APIRouter(prefix="/api", tags=["chat"])
logger = logging.getLogger(__name__)

MAX_TICKETS_PER_SESSION = 2


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
    return InitSessionResponse(
        session_id=session.session_id,
        greeting=greeting,
        items=_category_cards_items(),
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
            content=(
                "I'm sorry, something went wrong on my end. "
                "Please try again or raise a ticket and our team will help you."
            ),
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
    return _category_cards_items()


# ---------------------------------------------------------------------------
# Category selection
# ---------------------------------------------------------------------------

async def _handle_category_selection(session: SessionState, req: ChatRequest) -> List[ResponseItem]:
    if req.type != MessageInputType.SELECT_CATEGORY:
        return _category_cards_items()

    category = req.selected_id
    session.selected_category = category

    if category == "calls":
        return await _start_call_category_flow(session)
    if category == "transactions":
        return await _start_transaction_category_flow(session)
    if category == "other":
        session.stage = ConversationStage.AWAITING_OTHER_TEXT
        return [_text("Sure! Please tell me what issue you're facing and I'll do my best to help.")]

    return _category_cards_items()


# ---------------------------------------------------------------------------
# CALL category flow
# ---------------------------------------------------------------------------

async def _start_call_category_flow(session: SessionState) -> List[ResponseItem]:
    if not session.auth_token and not DUMMY_MODE:
        return _show_faq_cards(session)

    try:
        if session.user_type.value == "LISTENER":
            calls = await dostt_client.get_recent_listener_sessions(session.auth_token, limit=5)
        else:
            calls = await dostt_client.get_recent_calls(session.auth_token, limit=5)
        calls = [c for c in calls if not c.get("ticket_detail")]
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            session.stage = ConversationStage.ENDED
            return [_text(
                "I wasn't able to verify your session. "
                "Please close this chat and reopen it from the Dostt app."
            )]
        calls = []
    except Exception:
        calls = []

    if not calls:
        return _show_faq_cards(session)

    session.stage = ConversationStage.AWAITING_CALL_SELECTION
    return [
        _text("Please select the call you're having an issue with:"),
        ResponseItem(
            type=ResponseItemType.CALL_CARDS,
            data={"calls": calls, "prompt": "Select the call you're referring to:"},
        ),
    ]


async def _handle_call_selection(session: SessionState, req: ChatRequest) -> List[ResponseItem]:
    if req.type != MessageInputType.SELECT_CALL:
        return [_text("Please tap on one of the calls above to continue.")]

    selected_call = await _resolve_call(session, req.selected_id)
    if not selected_call:
        return [_text("I couldn't find that call. Please select one of the calls shown above.")]

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
    if session.user_type.value == "LISTENER":
        session.stage = ConversationStage.AWAITING_TRANSACTION_SUBTYPE
        return [
            _text("Which type of transaction would you like help with?"),
            ResponseItem(
                type=ResponseItemType.TRANSACTION_SUBTYPE_CARDS,
                data={
                    "options": [
                        {"id": "earnings", "label": "My Earnings"},
                        {"id": "payouts", "label": "My Payouts / Withdrawals"},
                    ]
                },
            ),
        ]
    return await _start_user_transaction_flow(session)


async def _handle_transaction_subtype(session: SessionState, req: ChatRequest) -> List[ResponseItem]:
    if req.type != MessageInputType.SELECT_TRANSACTION_SUBTYPE:
        return [_text("Please select one of the options above.")]

    subtype = req.selected_id
    session.selected_transaction_subtype = subtype

    if subtype == "payouts":
        return await _start_payout_flow(session)
    return await _start_earnings_flow(session)


async def _start_user_transaction_flow(session: SessionState) -> List[ResponseItem]:
    if not session.auth_token and not DUMMY_MODE:
        return _show_faq_cards(session)

    try:
        transactions = await dostt_client.get_recent_transactions(session.auth_token, limit=5)
        transactions = [t for t in transactions if not t.get("ticket_detail")]
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            session.stage = ConversationStage.ENDED
            return [_text(
                "I wasn't able to verify your session. "
                "Please close this chat and reopen it from the Dostt app."
            )]
        transactions = []
    except Exception:
        transactions = []

    if not transactions:
        return _show_faq_cards(session)

    session.stage = ConversationStage.AWAITING_TRANSACTION_SELECTION
    return [
        _text("Please select the transaction you're having an issue with:"),
        ResponseItem(
            type=ResponseItemType.TRANSACTION_CARDS,
            data={"transactions": transactions, "prompt": "Select the transaction you're referring to:"},
        ),
    ]


async def _start_earnings_flow(session: SessionState) -> List[ResponseItem]:
    if not session.auth_token and not DUMMY_MODE:
        return _show_faq_cards(session)

    try:
        transactions = await dostt_client.get_listener_earnings(session.auth_token, limit=5)
        transactions = [t for t in transactions if not t.get("ticket_detail")]
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            session.stage = ConversationStage.ENDED
            return [_text(
                "I wasn't able to verify your session. "
                "Please close this chat and reopen it from the Dostt app."
            )]
        transactions = []
    except Exception:
        transactions = []

    if not transactions:
        return _show_faq_cards(session)

    session.stage = ConversationStage.AWAITING_TRANSACTION_SELECTION
    return [
        _text("Please select the earning you're having an issue with:"),
        ResponseItem(
            type=ResponseItemType.TRANSACTION_CARDS,
            data={"transactions": transactions, "prompt": "Select the earning you're referring to:"},
        ),
    ]


async def _start_payout_flow(session: SessionState) -> List[ResponseItem]:
    if not session.auth_token and not DUMMY_MODE:
        return _show_faq_cards(session)

    try:
        payouts = await dostt_client.get_listener_payouts(session.auth_token, limit=5)
        payouts = [p for p in payouts if not p.get("ticket_detail")]
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            session.stage = ConversationStage.ENDED
            return [_text(
                "I wasn't able to verify your session. "
                "Please close this chat and reopen it from the Dostt app."
            )]
        payouts = []
    except Exception:
        payouts = []

    if not payouts:
        return _show_faq_cards(session)

    session.stage = ConversationStage.AWAITING_TRANSACTION_SELECTION
    return [
        _text("Please select the withdrawal you're having an issue with:"),
        ResponseItem(
            type=ResponseItemType.TRANSACTION_CARDS,
            data={"transactions": payouts, "prompt": "Select the withdrawal you're referring to:"},
        ),
    ]


async def _handle_transaction_selection(session: SessionState, req: ChatRequest) -> List[ResponseItem]:
    if req.type != MessageInputType.SELECT_TRANSACTION:
        return [_text("Please tap on one of the transactions above to continue.")]

    selected_tx = await _resolve_transaction(session, req.selected_id)
    if not selected_tx:
        return [_text("I couldn't find that transaction. Please select one from the list above.")]

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
        _text("What issue are you facing?"),
        ResponseItem(
            type=ResponseItemType.FAQ_CARDS,
            data={"faqs": [{"id": str(f.id), "title": f.title11} for f in faqs]},
        ),
    ]


async def _handle_faq_selection(session: SessionState, req: ChatRequest) -> List[ResponseItem]:
    if req.type != MessageInputType.SELECT_FAQ:
        return [_text("Please select one of the issues above.")]

    faq = faq_service.get_faq_by_id(req.selected_id or "")
    if not faq:
        return [_error()]

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

async def _handle_other_text(session: SessionState, req: ChatRequest) -> List[ResponseItem]:
    if not req.message:
        return [_text("Please type your question and I'll do my best to help.")]

    # Match against the full FAQ database visible to this user type
    all_faqs = faq_service.get_faqs_for_user_type(session.user_type.value)
    issue_id = await ai_service.identify_faq(req.message, session.user_type.value, all_faqs)
    faq = faq_service.get_faq_by_id(issue_id) if issue_id else None

    if not faq:
        if session.other_retry_count == 0:
            session.other_retry_count = 1
            # Stay in AWAITING_OTHER_TEXT so the next message retries
            return [_text(
                "I couldn't quite understand that. "
                "Could you rephrase or give a little more detail?"
            )]
        # Second failure — give up and direct to app support
        session.other_retry_count = 0
        return [
            _text(
                "I'm sorry, I couldn't identify the issue you're facing. "
                "Please raise a support ticket through the Help & Support section "
                "in the Dostt app and our support team will assist you further."
            ),
            *_ask_more_help(session),
        ]

    session.matched_faq_id = str(faq.id)
    session.original_message = req.message
    session.other_retry_count = 0

    # CALL FAQ — transition into the guided call flow
    if faq.type == IssueType.CALL:
        session.selected_category = "calls"
        session.preselected_faq_id = str(faq.id)
        return await _start_call_category_flow(session)

    # PAYMENT FAQ — transition into the appropriate payment flow
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

    # OTHER / ALL — answer directly
    return await _handle_other_issue(session, faq)


# ---------------------------------------------------------------------------
# OTHER issue handler (direct answer)
# ---------------------------------------------------------------------------

async def _handle_other_issue(session: SessionState, faq) -> List[ResponseItem]:
    answer_text = await ai_service.generate_initial_response(
        faq=faq,
        original_message=session.original_message or "",
        session=session,
    )
    items: List[ResponseItem] = [_text(answer_text)]

    if faq.feedback_type == FeedbackType.FEEDBACK_ONLY:
        items.extend(_ask_more_help(session))

    elif faq.feedback_type in (FeedbackType.RAISE_COMPLAINT_ONLY, FeedbackType.BOTH):
        if _ticket_limit_reached(session):
            items.append(_ticket_limit_reply())
            items.extend(_ask_more_help(session))
        else:
            session.stage = ConversationStage.ANSWERED
            items.append(_text("Are you still facing this issue?"))
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
        items.extend(_ask_more_help(session))

    elif faq.feedback_type == FeedbackType.RAISE_COMPLAINT_ONLY:
        if _ticket_limit_reached(session):
            items.append(_ticket_limit_reply())
            items.extend(_ask_more_help(session))
        else:
            session.stage = ConversationStage.AWAITING_TICKET_CONFIRMATION
            session.ticket_description = session.original_message
            items.append(_ticket_confirmation_item(session.ticket_description or "", faq.title11))

    elif faq.feedback_type == FeedbackType.BOTH:
        if _ticket_limit_reached(session):
            items.append(_ticket_limit_reply())
            items.extend(_ask_more_help(session))
        else:
            session.stage = ConversationStage.ANSWERED
            items.append(_text("Are you still facing this issue?"))
            items.append(_quick_replies_item())

    return items


# ---------------------------------------------------------------------------
# Ticket intent (ANSWERED stage)
# ---------------------------------------------------------------------------

async def _handle_ticket_intent(session: SessionState, req: ChatRequest) -> List[ResponseItem]:
    faq = faq_service.get_faq_by_id(session.matched_faq_id or "")

    if req.type == MessageInputType.CONFIRM_TICKET:
        if _ticket_limit_reached(session):
            items = [_ticket_limit_reply()]
            _reset_for_new_issue(session)
            items.extend(_category_cards_items())
            return items
        session.stage = ConversationStage.AWAITING_TICKET_CONFIRMATION
        session.ticket_description = session.original_message
        issue_name = faq.title11 if faq else "Support Request"
        return [_ticket_confirmation_item(session.ticket_description or "", issue_name)]

    if req.type == MessageInputType.CANCEL:
        return [_text("No problem!"), *_ask_more_help(session)]

    # Free-text fallback
    wants_ticket = await ai_service.classify_ticket_intent(req.message or "")
    if wants_ticket:
        if _ticket_limit_reached(session):
            items = [_ticket_limit_reply()]
            items.extend(_ask_more_help(session))
            return items
        session.stage = ConversationStage.AWAITING_TICKET_CONFIRMATION
        session.ticket_description = session.original_message
        issue_name = faq.title11 if faq else "Support Request"
        return [_ticket_confirmation_item(session.ticket_description or "", issue_name)]

    return [_text("Alright, I'm glad I could help!"), *_ask_more_help(session)]


# ---------------------------------------------------------------------------
# Ticket confirmation
# ---------------------------------------------------------------------------

async def _handle_ticket_confirmation(session: SessionState, req: ChatRequest) -> List[ResponseItem]:
    if req.type == MessageInputType.CANCEL:
        return [_text("Ticket creation cancelled."), *_ask_more_help(session)]

    if req.type == MessageInputType.EDIT_TICKET:
        session.stage = ConversationStage.AWAITING_TICKET_EDIT
        return [_text("Sure! Please type the description you'd like to use for this support ticket:")]

    if req.type == MessageInputType.CONFIRM_TICKET:
        return _ask_call_consent(session)

    text_lower = (req.message or "").lower()
    if any(w in text_lower for w in ["yes", "confirm", "create", "ok", "sure", "proceed"]):
        return _ask_call_consent(session)
    if any(w in text_lower for w in ["no", "cancel", "stop", "don't"]):
        return [_text("Ticket creation cancelled."), *_ask_more_help(session)]

    return [_text("Please use the buttons below to confirm, edit, or cancel the ticket.")]


async def _submit_ticket(session: SessionState) -> List[ResponseItem]:
    faq = faq_service.get_faq_by_id(session.matched_faq_id or "")
    if not faq:
        return [_error()]

    if not session.auth_token and not DUMMY_MODE:
        _reset_for_new_issue(session)
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
        await dostt_client.create_support_ticket(
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
        issue_name = faq.title11
        return [
            ResponseItem(type=ResponseItemType.TICKET_CREATED, data={"issue_name": issue_name}),
            _text("You can track your ticket in the Raised Tickets section under Help & Support."),
            *_ask_more_help(session),
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
# Call consent
# ---------------------------------------------------------------------------

def _ask_call_consent(session: SessionState) -> List[ResponseItem]:
    session.stage = ConversationStage.AWAITING_CALL_CONSENT
    hour = (datetime.now(tz=timezone.utc) + _IST).hour
    off_hours = hour < 9 or hour >= 19
    quick_reply_data: Dict[str, Any] = {
        "options": [
            {"id": "consent_yes", "label": "Yes, please call me"},
            {"id": "consent_no", "label": "No thanks"},
        ]
    }
    if off_hours:
        quick_reply_data["disclaimer"] = (
            "By submitting this request, you agree that our support team "
            "may reach out to you until 1:00 AM IST."
        )
    return [
        _text("Would you like the Dostt team to call you to help resolve this?"),
        ResponseItem(type=ResponseItemType.QUICK_REPLIES, data=quick_reply_data),
    ]


async def _handle_call_consent(session: SessionState, req: ChatRequest) -> List[ResponseItem]:
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

    return [_text("Please tap 'Yes, please call me' or 'No thanks' to continue.")]


# ---------------------------------------------------------------------------
# Fallback: no call/transaction data available
# ---------------------------------------------------------------------------

async def _fallback_to_no_data(session: SessionState, faq, entity: str) -> List[ResponseItem]:
    answer_text = await ai_service.generate_initial_response(
        faq=faq,
        original_message=session.original_message or "",
        session=session,
        context_note=f"No {entity} data is available. Answer directly without asking for selection.",
    )
    items: List[ResponseItem] = [_text(answer_text)]

    if faq.feedback_type == FeedbackType.FEEDBACK_ONLY:
        items.extend(_ask_more_help(session))

    elif faq.feedback_type in (FeedbackType.RAISE_COMPLAINT_ONLY, FeedbackType.BOTH):
        if _ticket_limit_reached(session):
            items.append(_ticket_limit_reply())
            items.extend(_ask_more_help(session))
        else:
            session.stage = ConversationStage.ANSWERED
            items.append(_text("Are you still facing this issue?"))
            items.append(_quick_replies_item())

    return items


# ---------------------------------------------------------------------------
# More help prompt
# ---------------------------------------------------------------------------

def _ask_more_help(session: SessionState) -> List[ResponseItem]:
    _reset_for_new_issue(session)
    session.stage = ConversationStage.AWAITING_MORE_HELP_RESPONSE
    return [
        _text("Is there anything else I can help you with?"),
        ResponseItem(
            type=ResponseItemType.QUICK_REPLIES,
            data={
                "options": [
                    {"id": "more_help_yes", "label": "Yes, I need help"},
                    {"id": "more_help_no", "label": "No thanks"},
                ]
            },
        ),
    ]


async def _handle_more_help_response(session: SessionState, req: ChatRequest) -> List[ResponseItem]:
    if req.type == MessageInputType.MORE_HELP_YES:
        _reset_for_new_issue(session)
        return _category_cards_items()

    if req.type == MessageInputType.MORE_HELP_NO:
        session.stage = ConversationStage.ENDED
        return [ResponseItem(
            type=ResponseItemType.CHAT_ENDED,
            content="Thank you for letting me help. You can close the chat window.",
        )]

    return [_text("Please use the buttons above to continue.")]


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


def _category_cards_items() -> List[ResponseItem]:
    return [
        ResponseItem(
            type=ResponseItemType.CATEGORY_CARDS,
            data={
                "options": [
                    {"id": "calls", "label": "Recent Calls", "icon": "phone"},
                    {"id": "transactions", "label": "Recent Transactions", "icon": "wallet"},
                    {"id": "other", "label": "Other Issues", "icon": "chat"},
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


def _ticket_limit_reply() -> ResponseItem:
    return _text(
        f"You can raise up to {MAX_TICKETS_PER_SESSION} tickets per chat session, "
        f"and you have already used all {MAX_TICKETS_PER_SESSION}. "
        "To raise more, please open a new support chat. "
        "You can track your existing tickets in the Raised Tickets section under Help & Support."
    )


def _out_of_scope_reply() -> str:
    return (
        "I'm sorry, I couldn't find a solution for that specific issue. "
        "Please try one of the categories below, or raise a ticket through Recent Calls or Transactions."
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
        is_payout = (faq_service.is_payout_faq(faq.id) if faq else False) or session.selected_transaction_subtype == "payouts"
        if is_payout:
            items = await dostt_client.get_listener_payouts(session.auth_token, limit=5)
        elif session.user_type.value == "LISTENER":
            items = await dostt_client.get_listener_earnings(session.auth_token, limit=5)
        else:
            items = await dostt_client.get_recent_transactions(session.auth_token, limit=5)
        found = next((t for t in items if str(t.get("id")) == str(tx_id)), None)
        return found or {"id": tx_id}
    except Exception:
        return {"id": tx_id}
