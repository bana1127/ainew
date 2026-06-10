from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.models import NotificationRule
from app.routers.notifications import delete_notification_rule
from app.services.notification_service import send_rule_now
from app.services.notification_target_service import get_targets_for_rule


class FakeDb:
    def __init__(self, rule):
        self.rule = rule
        self.committed = False

    def get(self, model, item_id):
        return self.rule if self.rule.id == item_id else None

    def commit(self):
        self.committed = True

    def rollback(self):
        return None

    def refresh(self, obj):
        return None


def _rule(deleted=False):
    rule = NotificationRule(
        id=uuid4(),
        name="삭제 테스트",
        enabled=True,
        reminder_type="activity_photo_missing",
        target_scope="activity",
        channel="gmail",
        template_subject="s",
        template_body="b",
    )
    if deleted:
        from datetime import datetime, timezone

        rule.deleted_at = datetime.now(timezone.utc)
        rule.enabled = False
    return rule


def test_delete_notification_rule_soft_deletes_and_keeps_history():
    rule = _rule()
    db = FakeDb(rule)

    deleted = delete_notification_rule(rule.id, db)

    assert deleted.deleted_at is not None
    assert deleted.enabled is False
    assert db.committed is True


def test_deleted_rule_is_excluded_from_due_targets():
    rule = _rule(deleted=True)

    assert get_targets_for_rule(db=object(), rule=rule) == []


def test_deleted_rule_cannot_send_now():
    rule = _rule(deleted=True)
    db = FakeDb(rule)

    with pytest.raises(HTTPException):
        send_rule_now(db, rule.id)
