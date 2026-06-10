from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from app.models import NotificationRule
from app.services.notification_target_service import (
    get_activity_fee_due_targets,
    get_membership_fee_due_targets,
)


class FakeDb:
    def __init__(self, rows, scalar_values):
        self.rows = rows
        self.scalar_values = list(scalar_values)

    def execute(self, statement):
        return self.rows

    def scalar(self, statement):
        return self.scalar_values.pop(0)


def test_membership_fee_notification_uses_semester_period_not_quarter():
    record = SimpleNamespace(
        id=uuid4(),
        required_amount=30000,
        paid_amount=0,
        status="unpaid",
    )
    member = SimpleNamespace(email="member@example.com", name="홍길동", is_executive=False)
    rule = NotificationRule(
        name="회비 미납",
        enabled=True,
        reminder_type="membership_fee_due",
        target_scope="term",
        channel="gmail",
        term="2026-1",
        quarter="2026-Q2",
        conditions={"include_statuses": ["unpaid"]},
        template_subject="{period} 회비 안내",
        template_body="{member_name}님 {period} 회비를 확인하세요. {target_url}",
    )
    db = FakeDb(rows=[(record, member)], scalar_values=[0])

    targets = get_membership_fee_due_targets(db, rule)

    assert len(targets) == 1
    assert "2026-1" in targets[0].subject
    assert "2026-Q2" not in targets[0].subject
    assert targets[0].target_url == "/payments"


def test_activity_fee_notification_uses_activity_link_not_payments():
    activity_id = uuid4()
    record = SimpleNamespace(
        id=uuid4(),
        required_amount=10000,
        paid_amount=0,
        status="unpaid",
    )
    member = SimpleNamespace(id=uuid4(), email="member@example.com", name="홍길동")
    activity = SimpleNamespace(id=activity_id, title="조향 활동", activity_date=None)
    rule = NotificationRule(
        name="활동비 미납",
        enabled=True,
        reminder_type="activity_fee_due",
        target_scope="activity",
        channel="gmail",
        activity_id=activity_id,
        conditions={"include_statuses": ["unpaid"], "exclude_cancelled": False},
        template_subject="{activity_title} 활동비 안내",
        template_body="{target_url}",
    )
    db = FakeDb(rows=[(record, member, activity)], scalar_values=[0])

    targets = get_activity_fee_due_targets(db, rule)

    assert len(targets) == 1
    assert targets[0].target_url == f"/activities/{activity_id}?tab=activity-fee"
    assert targets[0].target_url != "/payments"


def test_notification_rule_scopes_keep_domain_units_separate():
    membership = NotificationRule(
        name="회비",
        enabled=True,
        reminder_type="membership_fee_due",
        target_scope="term",
        channel="gmail",
        term="2026-1",
        template_subject="s",
        template_body="b",
    )
    evidence = NotificationRule(
        name="증빙",
        enabled=True,
        reminder_type="evidence_missing",
        target_scope="quarter",
        channel="gmail",
        quarter="2026-Q2",
        template_subject="s",
        template_body="b",
    )
    photo = NotificationRule(
        name="사진",
        enabled=True,
        reminder_type="activity_photo_missing",
        target_scope="activity",
        channel="gmail",
        days_after=2,
        template_subject="s",
        template_body="b",
    )

    assert membership.target_scope == "term"
    assert membership.term == "2026-1"
    assert evidence.target_scope == "quarter"
    assert evidence.quarter == "2026-Q2"
    assert photo.target_scope == "activity"
    assert photo.days_after == 2
