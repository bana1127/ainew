from __future__ import annotations

from app.models import NotificationRule
from app.schemas import NotificationRuleCreate, NotificationRuleUpdate
from app.services.notification_target_service import get_targets_for_rule


def test_notification_rule_create_schema_accepts_user_configurable_fields():
    payload = NotificationRuleCreate(
        name="활동 사진 누락",
        reminder_type="activity_photo_missing",
        target_scope="activity",
        channel="gmail",
        days_after=2,
        repeat_interval_days=2,
        max_send_count=3,
        require_confirm_before_send=True,
        conditions={"recipient_email": "ops@example.com"},
        template_subject="[ClubAgent] {activity_title} 사진 필요",
        template_body="{activity_title} 사진을 업로드하세요.",
    )

    assert payload.reminder_type == "activity_photo_missing"
    assert payload.days_after == 2
    assert payload.conditions["recipient_email"] == "ops@example.com"


def test_notification_rule_update_can_disable_rule():
    payload = NotificationRuleUpdate(enabled=False)

    assert payload.enabled is False


def test_disabled_rule_is_excluded_from_due_targets():
    rule = NotificationRule(
        name="비활성 규칙",
        enabled=False,
        reminder_type="custom",
        target_scope="global",
        channel="gmail",
        template_subject="subject",
        template_body="body",
    )

    assert get_targets_for_rule(db=None, rule=rule) == []
