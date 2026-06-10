from __future__ import annotations

from uuid import uuid4

from app.models import NotificationRule
from app.models import NotificationDeliveryLog
from app.schemas import NotificationDeliveryLogCreate
from app.services import notification_service
from app.services.notification_service import log_delivery_result
from app.services.notification_target_service import NotificationTarget


class FakeDb:
    def __init__(self):
        self.added = None
        self.committed = False

    def scalar(self, statement):
        return None

    def add(self, obj):
        self.added = obj

    def commit(self):
        self.committed = True

    def refresh(self, obj):
        return None

    def flush(self):
        if self.added is not None and self.added.id is None:
            self.added.id = uuid4()


def test_delivery_log_save_possible():
    db = FakeDb()

    log = log_delivery_result(
        db,
        NotificationDeliveryLogCreate(
            reminder_type="activity_photo_missing",
            target_type="activity",
            target_id="activity-1",
            recipient_email="ops@example.com",
            recipient_name="운영진",
            subject="사진 필요",
            body="본문",
            target_url="/activities/activity-1?tab=evidence",
            provider="n8n",
            provider_message_id="gmail-1",
            status="sent",
        ),
    )

    assert isinstance(log, NotificationDeliveryLog)
    assert db.committed is True
    assert log.status == "sent"
    assert log.sent_at is not None


def test_send_now_requests_n8n_service(monkeypatch):
    rule = NotificationRule(
        id=uuid4(),
        name="사진 누락",
        enabled=True,
        reminder_type="activity_photo_missing",
        target_scope="activity",
        channel="gmail",
        template_subject="subject",
        template_body="body",
    )
    called = {}
    db = FakeDb()

    monkeypatch.setattr(notification_service, "_get_active_rule", lambda session, rule_id: rule)
    monkeypatch.setattr(
        notification_service,
        "get_targets_for_rule",
        lambda session, loaded_rule: [
            NotificationTarget(
                target_type="activity",
                target_id="activity-1",
                recipient_email="ops@example.com",
                recipient_name="운영진",
                subject="사진 필요",
                body="본문",
                target_url="/activities/activity-1?tab=evidence",
                reason="활동 사진 없음",
            )
        ],
    )
    monkeypatch.setattr(
        notification_service.n8n_service,
        "send_notification_email",
        lambda payload: called.update({"payload": payload}) or {"message_id": "gmail-1"},
    )

    logs = notification_service.send_rule_now(db, rule.id)

    assert len(logs) == 1
    assert logs[0].status == "sent"
    assert called["payload"]["recipient_email"] == "ops@example.com"
