from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.core.config import settings


LAST_TEST_STATUS: str | None = None
LAST_TEST_AT: datetime | None = None


class N8nServiceError(RuntimeError):
    pass


def get_n8n_status() -> dict[str, Any]:
    return {
        "enabled": bool(settings.N8N_ENABLED),
        "webhook_configured": bool(settings.N8N_WEBHOOK_URL),
        "secret_configured": bool(settings.N8N_SECRET),
        "last_test_status": LAST_TEST_STATUS,
        "last_test_at": LAST_TEST_AT,
    }


def send_n8n_event(event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    if not settings.N8N_ENABLED:
        raise N8nServiceError("n8n integration is disabled.")
    if not settings.N8N_WEBHOOK_URL:
        raise N8nServiceError("N8N_WEBHOOK_URL is not configured.")

    body = json.dumps(
        {
            "event_type": event_type,
            "source": "clubagent",
            "payload": payload,
        },
        ensure_ascii=False,
    ).encode("utf-8")
    request = Request(
        settings.N8N_WEBHOOK_URL,
        data=body,
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "X-ClubAgent-Secret": settings.N8N_SECRET,
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=10) as response:  # nosec: configured webhook URL
            raw = response.read().decode("utf-8")
            if not raw:
                return {"ok": True, "status_code": response.status}
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                parsed = {"response": raw}
            parsed.setdefault("ok", 200 <= response.status < 300)
            parsed.setdefault("status_code", response.status)
            return parsed
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise N8nServiceError(f"n8n webhook failed with {exc.code}: {detail}") from exc
    except URLError as exc:
        raise N8nServiceError(f"Could not reach n8n webhook: {exc.reason}") from exc


def send_notification_email(payload: dict[str, Any]) -> dict[str, Any]:
    return send_n8n_event("notification_email", payload)


def send_test_email(payload: dict[str, Any]) -> dict[str, Any]:
    global LAST_TEST_AT, LAST_TEST_STATUS
    try:
        result = send_n8n_event("test_email", payload)
    except Exception:
        LAST_TEST_STATUS = "failed"
        LAST_TEST_AT = datetime.now(timezone.utc)
        raise
    LAST_TEST_STATUS = "success"
    LAST_TEST_AT = datetime.now(timezone.utc)
    return result
