from __future__ import annotations

from app.models import NotificationRule
from app.services.notification_seed_service import (
    DEFAULT_ACTIVITY_NOTIFICATION_RULES,
    ensure_default_notification_rules,
)


class FakeDb:
    def __init__(self, existing=None):
        self.existing = existing
        self.added = []
        self.commits = 0

    def scalar(self, statement):
        return self.existing

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.commits += 1

    def rollback(self):
        return None


def test_default_notification_rules_created_once():
    db = FakeDb(existing=None)

    created = ensure_default_notification_rules(db)

    assert created == len(DEFAULT_ACTIVITY_NOTIFICATION_RULES)
    assert len(db.added) == 4
    assert {rule.reminder_type for rule in db.added} == {
        "activity_photo_missing",
        "activity_upcoming",
        "activity_report_missing",
        "activity_evidence_missing",
    }


def test_default_notification_rules_not_duplicated():
    existing = NotificationRule(
        name="활동 사진 누락 알림",
        reminder_type="activity_photo_missing",
        target_scope="activity",
        channel="gmail",
        template_subject="사용자 제목",
        template_body="사용자 본문",
    )
    db = FakeDb(existing=existing)

    created = ensure_default_notification_rules(db)

    assert created == 0
    assert db.added == []


def test_default_seed_does_not_overwrite_user_modified_rule():
    existing = NotificationRule(
        name="사용자가 바꾼 활동 사진 알림",
        reminder_type="activity_photo_missing",
        target_scope="activity",
        channel="gmail",
        days_after=5,
        template_subject="사용자 제목",
        template_body="사용자 본문",
    )
    db = FakeDb(existing=existing)

    ensure_default_notification_rules(db)

    assert existing.days_after == 5
    assert existing.template_subject == "사용자 제목"
