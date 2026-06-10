from __future__ import annotations

from uuid import uuid4

from app.models import NotificationRule
from app.services import notification_service
from app.services.notification_target_service import NotificationTarget


def test_preview_rule_returns_target_subject_body_reason(monkeypatch):
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

    monkeypatch.setattr(notification_service, "_get_active_rule", lambda db, rule_id: rule)
    monkeypatch.setattr(
        notification_service,
        "get_targets_for_rule",
        lambda db, r: [
            NotificationTarget(
                target_type="activity",
                target_id="activity-1",
                recipient_email="ops@example.com",
                recipient_name="운영진",
                subject="[ClubAgent] 사진 필요",
                body="본문",
                target_url="/activities/activity-1?tab=evidence",
                reason="활동일 후 2일 경과, 활동 사진 없음",
            )
        ],
    )

    preview = notification_service.preview_rule(db=object(), rule_id=rule.id)

    assert preview.count == 1
    assert preview.items[0].recipient_email == "ops@example.com"
    assert "활동 사진" in preview.items[0].reason
