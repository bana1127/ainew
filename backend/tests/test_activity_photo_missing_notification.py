from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from uuid import uuid4

from app.models import NotificationRule
from app.services.evidence_parser_service import policy_for_document_type
from app.services.notification_target_service import get_activity_photo_missing_targets


class FakeDb:
    def __init__(self, scalar_values, scalar_rows):
        self.scalar_values = list(scalar_values)
        self.scalar_rows = scalar_rows

    def scalar(self, statement):
        return self.scalar_values.pop(0)

    def scalars(self, statement):
        return self.scalar_rows


def _rule() -> NotificationRule:
    return NotificationRule(
        name="활동 사진 누락",
        enabled=True,
        reminder_type="activity_photo_missing",
        target_scope="activity",
        channel="gmail",
        days_after=2,
        repeat_interval_days=2,
        max_send_count=3,
        require_confirm_before_send=True,
        conditions={"recipient_email": "ops@example.com", "recipient_name": "운영진"},
        template_subject="[ClubAgent] {activity_title} 활동 사진 업로드 필요",
        template_body="{activity_title} 사진을 업로드하세요. {target_url}",
    )


def test_activity_photo_document_type_does_not_require_amount():
    status, need_check, reason = policy_for_document_type("activity_photo", None)

    assert status == "valid"
    assert need_check is False
    assert "활동 사진" in reason


def test_activity_photo_missing_uses_activity_date_plus_days_after():
    activity_id = uuid4()
    activity = SimpleNamespace(
        id=activity_id,
        title="위퍼퓸 교내조향활동",
        activity_date=date(2020, 1, 1),
    )
    db = FakeDb(
        scalar_values=[
            0,
            0,
            0,
        ],
        scalar_rows=[activity],
    )

    targets = get_activity_photo_missing_targets(db, _rule())

    assert len(targets) == 1
    assert targets[0].target_url == f"/activities/{activity_id}?tab=evidence"
    assert "활동 사진 없음" in targets[0].reason


def test_activity_photo_present_excludes_missing_target():
    activity = SimpleNamespace(
        id=uuid4(),
        title="위퍼퓸 교내조향활동",
        activity_date=date(2020, 1, 1),
    )
    db = FakeDb(
        scalar_values=[1],
        scalar_rows=[activity],
    )

    assert get_activity_photo_missing_targets(db, _rule()) == []


def test_activity_photo_missing_excludes_when_max_send_count_reached():
    activity = SimpleNamespace(
        id=uuid4(),
        title="위퍼퓸 교내조향활동",
        activity_date=date(2020, 1, 1),
    )
    db = FakeDb(scalar_values=[0, 3], scalar_rows=[activity])

    assert get_activity_photo_missing_targets(db, _rule()) == []


def test_activity_photo_missing_excludes_within_repeat_interval():
    activity = SimpleNamespace(
        id=uuid4(),
        title="위퍼퓸 교내조향활동",
        activity_date=date(2020, 1, 1),
    )
    db = FakeDb(scalar_values=[0, 0, 1], scalar_rows=[activity])

    assert get_activity_photo_missing_targets(db, _rule()) == []
