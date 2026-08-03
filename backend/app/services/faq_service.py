import json
import logging
import re
from pathlib import Path
from typing import List, Optional

from app.config import settings
from app.models.faq import FAQ, IssueType, Visibility

# FAQ IDs that belong to the LISTENER payouts (withdrawal) flow.
# All are type=2 in the system; this set distinguishes them from earnings FAQs.
_PAYOUT_FAQ_IDS: frozenset[int] = frozenset({336, 337})

logger = logging.getLogger(__name__)

_faqs: List[FAQ] = []


# ---------------------------------------------------------------------------
# HTML → plain text
# ---------------------------------------------------------------------------

def _html_to_text(html: str) -> str:
    """Convert FAQ HTML answers to readable plain text for AI consumption."""
    text = html
    # Convert block elements to newlines before stripping tags
    text = re.sub(r"</p>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</li>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<li[^>]*>", "• ", text, flags=re.IGNORECASE)
    text = re.sub(r"</ul>|</ol>", "\n", text, flags=re.IGNORECASE)
    # Strip all remaining tags
    text = re.sub(r"<[^>]+>", "", text)
    # Decode common HTML entities
    replacements = {
        "&nbsp;": " ", "&mdash;": "—", "&ndash;": "–",
        "&ldquo;": '"', "&rdquo;": '"', "&lsquo;": "'", "&rsquo;": "'",
        "&amp;": "&", "&lt;": "<", "&gt;": ">",
        "&bull;": "•", "&hellip;": "...", "&trade;": "™", "&copy;": "©",
    }
    for entity, char in replacements.items():
        text = text.replace(entity, char)
    # Collapse multiple blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------

def load_faqs() -> None:
    global _faqs
    faq_path = Path(settings.FAQ_FILE_PATH)
    if not faq_path.exists():
        logger.error("FAQ file not found at %s", faq_path)
        _faqs = []
        return
    with open(faq_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    loaded = []
    for item in raw:
        faq = FAQ(**item)
        faq.answer_plain = _html_to_text(faq.answer)
        loaded.append(faq)

    _faqs = loaded
    logger.info("Loaded %d FAQs", len(_faqs))


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------

def get_faqs_for_user_type(user_type: str) -> List[FAQ]:
    """
    Return FAQs visible to the given user type.
      USER     (CUSTOMER=0) → visibility CUSTOMER or BOTH
      LISTENER (EXPERT=1)   → visibility EXPERT or BOTH
    """
    if user_type.upper() == "USER":
        return [f for f in _faqs if f.visibility in (Visibility.CUSTOMER, Visibility.BOTH)]
    else:
        return [f for f in _faqs if f.visibility in (Visibility.EXPERT, Visibility.BOTH)]


def get_faq_by_id(faq_id: str) -> Optional[FAQ]:
    """Accept the id as a string (as returned from the AI) and match by int."""
    try:
        id_int = int(faq_id)
        return next((f for f in _faqs if f.id == id_int), None)
    except (ValueError, TypeError):
        return None


def get_faqs_by_issue_type_and_user_type(issue_type: IssueType, user_type: str) -> List[FAQ]:
    if user_type.upper() == "USER":
        visible = [f for f in _faqs if f.visibility in (Visibility.CUSTOMER, Visibility.BOTH)]
    else:
        visible = [f for f in _faqs if f.visibility in (Visibility.EXPERT, Visibility.BOTH)]
    return [f for f in visible if f.type == issue_type]


def is_payout_faq(faq_id: int) -> bool:
    return faq_id in _PAYOUT_FAQ_IDS


def get_listener_payout_faqs() -> List[FAQ]:
    """FAQs shown in the LISTENER My Payouts / Withdrawals flow."""
    return [f for f in _faqs if f.id in _PAYOUT_FAQ_IDS
            and f.visibility in (Visibility.EXPERT, Visibility.BOTH)]


def get_listener_earnings_faqs() -> List[FAQ]:
    """FAQs shown in the LISTENER My Earnings flow (type=2, not in payout set)."""
    return [f for f in _faqs
            if f.type == IssueType.PAYMENT
            and f.visibility in (Visibility.EXPERT, Visibility.BOTH)
            and f.id not in _PAYOUT_FAQ_IDS]


def get_all_faqs() -> List[FAQ]:
    return list(_faqs)
