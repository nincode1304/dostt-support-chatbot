import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional

from app.config import settings
from app.models.session import SessionState, UserType

logger = logging.getLogger(__name__)

_sessions: Dict[str, SessionState] = {}


def create_session(auth_token: Optional[str], user_type: str, language: str = "English", platform: str = "Android", app_version_code: str = "131") -> SessionState:
    session_id = str(uuid.uuid4())
    parsed_type = UserType.LISTENER if user_type.upper() == "LISTENER" else UserType.USER
    session = SessionState(
        session_id=session_id,
        auth_token=auth_token,
        user_type=parsed_type,
        language=language,
        platform=platform,
        app_version_code=app_version_code,
    )
    _sessions[session_id] = session
    logger.debug("Created session %s for user_type=%s language=%s platform=%s", session_id, parsed_type, language, platform)
    return session


def get_session(session_id: str) -> Optional[SessionState]:
    session = _sessions.get(session_id)
    if session is None:
        return None
    if _is_expired(session):
        del _sessions[session_id]
        return None
    return session


def save_session(session: SessionState) -> None:
    session.last_activity = datetime.now()
    _sessions[session.session_id] = session


def delete_session(session_id: str) -> None:
    _sessions.pop(session_id, None)


def _is_expired(session: SessionState) -> bool:
    ttl = timedelta(seconds=settings.SESSION_TTL_SECONDS)
    return datetime.now() - session.last_activity > ttl


async def cleanup_loop() -> None:
    """Periodically remove expired sessions."""
    while True:
        await asyncio.sleep(300)
        expired = [sid for sid, s in list(_sessions.items()) if _is_expired(s)]
        for sid in expired:
            del _sessions[sid]
        if expired:
            logger.info("Cleaned up %d expired sessions", len(expired))
