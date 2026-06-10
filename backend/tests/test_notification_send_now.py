from __future__ import annotations

from uuid import uuid4

from app.models import NotificationRule
from app.services import notification_service
from app.services.notification_target_service import NotificationTarget


class FakeDb:
    def __init__(self, rule):
        self.rule = rule
        self.added = []
        self.committed = False

    def get(self, model, item_id):
        return self.rule if item_id == self.rule.id else None

    def add(self, obj):
        if obj.id is None:
            obj.id = uuid4()
        self.added.append(obj)

    def flush(self):
        return None

    def commit(self):
        self.committed = True

    def refresh(self, obj):
        return None


def test_send_now_calls_n8n_and_saves_delivery_log(monkeypatch):
    rule = NotificationRule(
        id=uuid4(),
        name="활동 사진 누락 알림",
        enabled=True,
        reminder_type="activity_photo_missing",
        target_scope="activity",
        channel="gmail",
        template_subject="s",
        template_body="b",
    )
    db = FakeDb(rule)
    called = {}

    monkeypatch.setattr(
        notification_service,
        "get_targets_for_rule",
        lambda session, loaded_rule: [
            NotificationTarget(
                target_type="activity",
                target_id="activity-1",
                recipient_email="club@example.com",
                recipient_name="운영진",
                subject="[ClubAgent] 활동 사진 업로드 필요: 위퍼퓸",
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

    assert db.committed is True
    assert len(db.added) == 1
    assert logs[0].status == "sent"
    assert logs[0].provider_message_id == "gmail-1"
    assert called["payload"]["reminder_type"] == "activity_photo_missing"
