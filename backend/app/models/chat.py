from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class MessageInputType(str, Enum):
    TEXT = "text"
    SELECT_CALL = "select_call"
    SELECT_TRANSACTION = "select_transaction"
    CONFIRM_TICKET = "confirm_ticket"
    EDIT_TICKET = "edit_ticket"
    CANCEL = "cancel"
    CONSENT_YES = "consent_yes"
    CONSENT_NO = "consent_no"


class ResponseItemType(str, Enum):
    TEXT = "text"
    CALL_CARDS = "call_cards"
    TRANSACTION_CARDS = "transaction_cards"
    TICKET_CONFIRMATION = "ticket_confirmation"
    TICKET_CREATED = "ticket_created"
    QUICK_REPLIES = "quick_replies"
    ERROR = "error"


class QuickReplyOption(BaseModel):
    id: str
    label: str


class ResponseItem(BaseModel):
    type: ResponseItemType
    content: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class InitSessionRequest(BaseModel):
    auth_token: Optional[str] = None
    user_type: str = "USER"


class InitSessionResponse(BaseModel):
    session_id: str
    greeting: str


class ChatRequest(BaseModel):
    session_id: str = Field(max_length=64)
    type: MessageInputType = MessageInputType.TEXT
    message: Optional[str] = Field(default=None, max_length=2000)
    selected_id: Optional[str] = Field(default=None, max_length=64)
    edited_description: Optional[str] = Field(default=None, max_length=2000)
    consent_call: Optional[bool] = None


class ChatResponse(BaseModel):
    session_id: str
    items: List[ResponseItem]
