from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class ConversationStage(str, Enum):
    INITIAL = "INITIAL"
    AWAITING_CATEGORY_SELECTION = "AWAITING_CATEGORY_SELECTION"
    AWAITING_TRANSACTION_SUBTYPE = "AWAITING_TRANSACTION_SUBTYPE"
    AWAITING_CALL_SELECTION = "AWAITING_CALL_SELECTION"
    AWAITING_TRANSACTION_SELECTION = "AWAITING_TRANSACTION_SELECTION"
    AWAITING_FAQ_SELECTION = "AWAITING_FAQ_SELECTION"
    AWAITING_OTHER_TEXT = "AWAITING_OTHER_TEXT"
    AWAITING_MORE_HELP_RESPONSE = "AWAITING_MORE_HELP_RESPONSE"
    ANSWERED = "ANSWERED"
    AWAITING_TICKET_CONFIRMATION = "AWAITING_TICKET_CONFIRMATION"
    AWAITING_TICKET_EDIT = "AWAITING_TICKET_EDIT"
    AWAITING_CALL_CONSENT = "AWAITING_CALL_CONSENT"
    TICKET_CREATED = "TICKET_CREATED"
    ENDED = "ENDED"


class UserType(str, Enum):
    USER = "USER"
    LISTENER = "LISTENER"


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)


class SessionState(BaseModel):
    session_id: str
    user_type: UserType = UserType.USER
    auth_token: Optional[str] = None
    language: str = "English"
    platform: str = "Android"
    app_version_code: str = "131"
    matched_faq_id: Optional[str] = None
    selected_call: Optional[Dict[str, Any]] = None
    selected_transaction: Optional[Dict[str, Any]] = None
    original_message: Optional[str] = None
    ticket_description: Optional[str] = None
    consent_call: Optional[bool] = None
    tickets_raised: int = 0
    selected_category: Optional[str] = None
    selected_transaction_subtype: Optional[str] = None
    preselected_faq_id: Optional[str] = None  # FAQ matched from Other free-text, auto-used after entity selection
    other_retry_count: int = 0
    stage: ConversationStage = ConversationStage.AWAITING_CATEGORY_SELECTION
    messages: List[ChatMessage] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    last_activity: datetime = Field(default_factory=datetime.now)
