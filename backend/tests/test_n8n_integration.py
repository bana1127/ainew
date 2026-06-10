from __future__ import annotations

from app.routers.integrations import get_n8n_status, send_n8n_test
from app.schemas import N8nTestPayload
from app.services import n8n_service


def test_n8n_status_api_returns_configuration(monkeypatch):
    monkeypatch.setattr(n8n_service.settings, "N8N_ENABLED", True)
    monkeypatch.setattr(n8n_service.settings, "N8N_WEBHOOK_URL", "https://n8n.example/webhook")
    monkeypatch.setattr(n8n_service.settings, "N8N_SECRET", "secret")

    status = get_n8n_status()

    assert status["enabled"] is True
    assert status["webhook_configured"] is True
    assert status["secret_configured"] is True


def test_n8n_test_api_calls_service(monkeypatch):
    called = {}

    def fake_send_test_email(payload):
        called["payload"] = payload
        return {"ok": True}

    monkeypatch.setattr(n8n_service, "send_test_email", fake_send_test_email)

    result = send_n8n_test(
        N8nTestPayload(recipient_email="club@example.com", subject="test", body="body")
    )

    assert result.ok is True
    assert called["payload"]["recipient_email"] == "club@example.com"
