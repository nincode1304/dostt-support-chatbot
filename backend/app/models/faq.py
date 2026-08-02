from enum import IntEnum
from typing import List, Optional
from pydantic import BaseModel


class Visibility(IntEnum):
    CUSTOMER = 0  # USER in mobile app
    EXPERT = 1    # LISTENER in mobile app
    BOTH = 2


class IssueType(IntEnum):
    OTHER = 0
    CALL = 1
    PAYMENT = 2   # USER coin transactions / LISTENER earnings (booking-tied)
    ALL = 3       # General FAQ — treated as OTHER in conversation flow
    PAYOUT = 4    # LISTENER withdrawal to bank/UPI (dosttexpertpayout)


class FeedbackType(IntEnum):
    FEEDBACK_ONLY = 1         # Answer only, no ticket
    RAISE_COMPLAINT_ONLY = 2  # Raise a ticket (answer briefly then ticket)
    BOTH = 3                  # Answer + offer to raise ticket


class FAQ(BaseModel):
    id: int
    name: str           # Internal category name (e.g. "KYC- How Do I complete my KYC")
    visibility: Visibility
    type: IssueType
    title11: str        # User-facing question
    answer: str         # Original HTML answer
    feedback_type: FeedbackType
    answer_plain: str = ""  # HTML-stripped, populated at load time

    class Config:
        use_enum_values = False
