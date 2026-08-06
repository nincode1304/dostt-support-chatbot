"""
Dostt API client.

Set DUMMY_MODE=true in .env to use hardcoded test data (no real API calls).

Endpoints (same for staging and production):
  USER:
    GET  /help-and-support/bookings/customers/     -> call history
    GET  /help-and-support/payments/transactions   -> coin transactions

  LISTENER (listener JWT, Service-Type: 1):
    GET  /help-and-support/bookings/experts/       -> session history
    GET  /help-and-support/payments/earnings/      -> earnings
    GET  /help-and-support/payments/payouts/       -> payout history

  BOTH:
    POST /help-and-support/tickets/                -> create ticket

Auth: JWT-AUTHORIZATION: Bearer <token>
"""

import logging
from typing import Any, Dict, List, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

DUMMY_MODE = settings.DUMMY_MODE

_BASE_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "app-version": "1.1.31",
    "app-version-code": "131",
    "X-Country-Code": "IN",
    "X-Pricing-Country-code": "IN",
    "X-App-Open-Count": "4",
    "X-Platform-Type": "Android",
}

# ---------------------------------------------------------------------------
# Dummy data — exact shape from real API response (24 Jul 2026 sample)
# ---------------------------------------------------------------------------

_DUMMY_CALLS = [
    {
        "id": 40549,
        "booking_date": "24th Jul",
        "type": "Audio",
        "session_id": "DOSTT24Jul2640549",
        "booked_at": "2026-07-24T16:23:37.983294+05:30",
        "gifts_count": 0,
        "ticket_detail": {"id": 2081, "status": 2, "is_viewed": True},
        "total_duration": "23 m",
        "duration": "23 m",
        "expert": {
            "id": 706,
            "name": "piyush_test",
            "thumb_url": "https://cdn-gyani-staging.getlokalapp.com/cache/6e/bc/6ebcc2da82cd73134e4ed5cb3fa23e5f.webp",
        },
        "coins": 345,
    },
    {
        "id": 40548,
        "booking_date": "24th Jul",
        "type": "Video",
        "session_id": "DOSTT24Jul2640548",
        "booked_at": "2026-07-24T16:17:17.781774+05:30",
        "gifts_count": 0,
        "ticket_detail": None,
        "total_duration": "02 m",
        "duration": "02 m",
        "expert": {
            "id": 627,
            "name": "premium_male_pawansdt1",
            "thumb_url": "https://cdn-gyani-staging.getlokalapp.com/cache/23/57/2357385517b502a43754125f02e03a70.webp",
        },
        "coins": 180,
    },
    {
        "id": 40531,
        "booking_date": "22nd Jul",
        "type": "Audio",
        "session_id": "DOSTT22Jul2640531",
        "booked_at": "2026-07-22T11:05:10.000000+05:30",
        "gifts_count": 1,
        "ticket_detail": None,
        "total_duration": "45 m",
        "duration": "45 m",
        "expert": {
            "id": 701,
            "name": "listener_ananya",
            "thumb_url": "",
        },
        "coins": 675,
    },
]

_DUMMY_TRANSACTIONS = [
    {
        "id": 10731,
        "amount": 98,
        "title": "Wallet Recharge",
        "status": 1,
        "coins": 100,
        "created_on": "2026-07-29T23:22:14.093111+05:30",
        "ticket_detail": None,
    },
    {
        "id": 10728,
        "amount": 0,
        "title": "Call Deduction",
        "status": 1,
        "coins": 345,
        "created_on": "2026-07-24T16:23:37.000000+05:30",
        "ticket_detail": None,
    },
    {
        "id": 10725,
        "amount": 0,
        "title": "Call Deduction",
        "status": 1,
        "coins": 180,
        "created_on": "2026-07-24T16:17:17.000000+05:30",
        "ticket_detail": None,
    },
    {
        "id": 10710,
        "amount": 49,
        "title": "Wallet Recharge",
        "status": 1,
        "coins": 50,
        "created_on": "2026-07-20T09:30:00.000000+05:30",
        "ticket_detail": None,
    },
]

_DUMMY_LISTENER_SESSIONS = [
    {
        "id": 40938,
        "booking_date": "30th Jul",
        "type": "Audio_to_video",
        "session_id": "DOSTT30Jul2640938",
        "booked_at": "2026-07-30T16:45:46.891585+05:30",
        "gifts_count": 0,
        "ticket_detail": {"id": 2088, "status": 2, "is_viewed": True},
        "duration": {"audio": "17 m 39 s", "video": "24 s"},
        "total_duration": "18 m 03 s",
        "customer": {
            "id": 1291,
            "name": "prkhruser",
            "thumb_url": "https://cdn-gyani-staging.getlokalapp.com/cache/6e/bc/6ebcc2da82cd73134e4ed5cb3fa23e5f.webp",
        },
    },
    {
        "id": 40936,
        "booking_date": "30th Jul",
        "type": "Audio",
        "session_id": "DOSTT30Jul2640936",
        "booked_at": "2026-07-30T16:09:47.784015+05:30",
        "gifts_count": 0,
        "ticket_detail": None,
        "duration": "05 m 41 s",
        "total_duration": "05 m 41 s",
        "customer": {
            "id": 1291,
            "name": "prkhruser",
            "thumb_url": "https://cdn-gyani-staging.getlokalapp.com/cache/6e/bc/6ebcc2da82cd73134e4ed5cb3fa23e5f.webp",
        },
    },
    {
        "id": 40918,
        "booking_date": "30th Jul",
        "type": "Audio",
        "session_id": "DOSTT29Jul2640918",
        "booked_at": "2026-07-30T01:15:09.086623+05:30",
        "gifts_count": 0,
        "ticket_detail": {"id": 2086, "status": 2, "is_viewed": False},
        "duration": "02 m 47 s",
        "total_duration": "02 m 47 s",
        "customer": {
            "id": 1291,
            "name": "prkhruser",
            "thumb_url": "https://cdn-gyani-staging.getlokalapp.com/cache/6e/bc/6ebcc2da82cd73134e4ed5cb3fa23e5f.webp",
        },
    },
]


def _auth_headers(token: str, service_type: str = "1", platform: str = "Android", app_version_code: str = "131") -> Dict[str, str]:
    return {
        **_BASE_HEADERS,
        "JWT-AUTHORIZATION": f"Bearer {token}",
        "Service-Type": service_type,
        "X-Platform-Type": platform,
        "app-version-code": app_version_code,
    }


# ---------------------------------------------------------------------------
# Calls (Users)
# ---------------------------------------------------------------------------

async def get_recent_calls(token: str, limit: int = 5, platform: str = "Android", app_version_code: str = "131") -> List[Dict[str, Any]]:
    if DUMMY_MODE:
        logger.info("DUMMY_MODE: returning %d fake calls", min(limit, len(_DUMMY_CALLS)))
        return _DUMMY_CALLS[:limit]

    url = f"{settings.DOSTT_API_BASE_URL}/help-and-support/bookings/customers/"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers=_auth_headers(token, platform=platform, app_version_code=app_version_code))
        resp.raise_for_status()
        return resp.json().get("results", [])[:limit]
    except httpx.HTTPStatusError as e:
        logger.error("Dostt calls API HTTP %s: %s", e.response.status_code, e)
        raise
    except Exception as e:
        logger.error("Dostt calls API error: %s", e)
        raise


# ---------------------------------------------------------------------------
# Transactions (Users)
# ---------------------------------------------------------------------------

async def get_recent_transactions(token: str, limit: int = 5, platform: str = "Android", app_version_code: str = "131") -> List[Dict[str, Any]]:
    if DUMMY_MODE:
        logger.info("DUMMY_MODE: returning %d fake transactions", min(limit, len(_DUMMY_TRANSACTIONS)))
        return _DUMMY_TRANSACTIONS[:limit]

    url = f"{settings.DOSTT_API_BASE_URL}/help-and-support/payments/transactions"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers=_auth_headers(token, platform=platform, app_version_code=app_version_code))
        resp.raise_for_status()
        return resp.json().get("results", [])[:limit]
    except httpx.HTTPStatusError as e:
        logger.error("Dostt transactions API HTTP %s: %s", e.response.status_code, e)
        raise
    except Exception as e:
        logger.error("Dostt transactions API error: %s", e)
        raise


# ---------------------------------------------------------------------------
# Listener Sessions
# ---------------------------------------------------------------------------

async def get_recent_listener_sessions(token: str, limit: int = 5, platform: str = "Android", app_version_code: str = "131") -> List[Dict[str, Any]]:
    if DUMMY_MODE:
        logger.info("DUMMY_MODE: returning %d fake listener sessions", min(limit, len(_DUMMY_LISTENER_SESSIONS)))
        return _DUMMY_LISTENER_SESSIONS[:limit]

    url = f"{settings.DOSTT_API_BASE_URL}/help-and-support/bookings/experts/"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers=_auth_headers(token, platform=platform, app_version_code=app_version_code))
        resp.raise_for_status()
        return resp.json().get("results", [])[:limit]
    except httpx.HTTPStatusError as e:
        logger.error("Dostt listener sessions API HTTP %s: %s", e.response.status_code, e)
        raise
    except Exception as e:
        logger.error("Dostt listener sessions API error: %s", e)
        raise


# ---------------------------------------------------------------------------
# Listener Payments (earnings + payouts) — used for PAYMENT flow for LISTENERs
# ---------------------------------------------------------------------------

_DUMMY_EARNINGS = [
    {
        "id": 40548,
        "title": "Call Earning",
        "amount": 45,
        "status": 1,
        "coins": 0,
        "created_on": "2026-07-24T16:17:17.000000+05:30",
        "ticket_detail": None,
    },
    {
        "id": 40531,
        "title": "Call Earning",
        "amount": 112,
        "status": 1,
        "coins": 0,
        "created_on": "2026-07-22T11:05:10.000000+05:30",
        "ticket_detail": None,
    },
    {
        "id": 40936,
        "title": "Call Earning",
        "amount": 28,
        "status": 2,
        "coins": 0,
        "created_on": "2026-07-30T16:09:47.000000+05:30",
        "ticket_detail": {"id": 2088, "status": 2, "is_viewed": True},
    },
]


async def get_listener_earnings(token: str, limit: int = 5, platform: str = "Android", app_version_code: str = "131") -> List[Dict[str, Any]]:
    if DUMMY_MODE:
        logger.info("DUMMY_MODE: returning %d fake earnings", min(limit, len(_DUMMY_EARNINGS)))
        return _DUMMY_EARNINGS[:limit]

    url = f"{settings.DOSTT_API_BASE_URL}/help-and-support/payments/earnings/"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers=_auth_headers(token, platform=platform, app_version_code=app_version_code))
        resp.raise_for_status()
        return resp.json().get("results", [])[:limit]
    except httpx.HTTPStatusError as e:
        logger.error("Dostt earnings API HTTP %s: %s", e.response.status_code, e)
        raise
    except Exception as e:
        logger.error("Dostt earnings API error: %s", e)
        raise


_DUMMY_PAYOUTS = [
    {
        "id": 5021,
        "title": "Withdrawal",
        "amount": 500,
        "status": 1,
        "created_on": "2026-07-28T10:30:00.000000+05:30",
        "ticket_detail": None,
    },
    {
        "id": 5018,
        "title": "Withdrawal",
        "amount": 1200,
        "status": 2,
        "created_on": "2026-07-20T14:15:00.000000+05:30",
        "ticket_detail": None,
    },
]


async def get_listener_payouts(token: str, limit: int = 5, platform: str = "Android", app_version_code: str = "131") -> List[Dict[str, Any]]:
    if DUMMY_MODE:
        logger.info("DUMMY_MODE: returning %d fake payouts", min(limit, len(_DUMMY_PAYOUTS)))
        return _DUMMY_PAYOUTS[:limit]

    url = f"{settings.DOSTT_API_BASE_URL}/help-and-support/payments/payouts/"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers=_auth_headers(token, platform=platform, app_version_code=app_version_code))
        resp.raise_for_status()
        return resp.json().get("results", [])[:limit]
    except httpx.HTTPStatusError as e:
        logger.error("Dostt payouts API HTTP %s: %s", e.response.status_code, e)
        raise
    except Exception as e:
        logger.error("Dostt payouts API error: %s", e)
        raise


# ---------------------------------------------------------------------------
# Ticket Creation
# ---------------------------------------------------------------------------

async def create_support_ticket(
    token: str,
    issue_id: str,
    description: str,
    reference_entity_id: Optional[str] = None,
    reference_entity_type: Optional[str] = None,
    issue_type: int = 0,
    user_type: str = "USER",
    consent_call: bool = False,
    language: str = "2",
    platform: str = "Android",
    app_version_code: str = "131",
) -> Dict[str, Any]:
    if DUMMY_MODE:
        import random, string
        fake_id = "TKT-" + "".join(random.choices(string.digits, k=6))
        payload_preview = {
            "description": description,
            "issues": str(issue_id),
            "languages": language,
            "is_call_opted_in": "true" if consent_call else "false",
            "type": str(issue_type),
            **({"reference_entity_id": str(reference_entity_id)} if reference_entity_id else {}),
            **({"reference_entity_type": reference_entity_type} if reference_entity_type else {}),
        }
        logger.info("DUMMY_MODE ticket payload → %s", payload_preview)
        logger.info("DUMMY_MODE ticket created: %s", fake_id)
        return {"ticket_id": fake_id, "status": "open"}

    url = f"{settings.DOSTT_API_BASE_URL}/help-and-support/tickets/"

    # Build multipart/form-data fields
    # httpx sends multipart when `files=` is used; (None, value) means a plain text field
    form: Dict[str, Any] = {
        "description": (None, description),
        "issues": (None, str(issue_id)),
        "languages": (None, language),
        "is_call_opted_in": (None, "true" if consent_call else "false"),
        "type": (None, str(issue_type)),
    }
    if reference_entity_id is not None:
        form["reference_entity_id"] = (None, str(reference_entity_id))
    if reference_entity_type is not None:
        form["reference_entity_type"] = (None, reference_entity_type)

    service_type = "1"  # both USER and LISTENER use Service-Type: 1
    log_payload = {k: v[1] for k, v in form.items()}
    logger.info("Ticket create REQUEST → url=%s payload=%s", url, log_payload)
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                url,
                files=form,
                headers=_auth_headers(token, service_type=service_type, platform=platform, app_version_code=app_version_code),
            )
        logger.info("Ticket create RESPONSE → status=%s body=%s", resp.status_code, resp.text)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as e:
        logger.error("Dostt ticket create HTTP %s: %s", e.response.status_code, e.response.text)
        raise
    except Exception as e:
        logger.error("Dostt ticket create error: %s", e)
        raise
