from __future__ import annotations

from datetime import date

from app.services.activity_photo_service import build_activity_photo_checklist_item


def test_activity_photo_checklist_done_when_photo_exists():
    item = build_activity_photo_checklist_item(
        photo_count=1,
        activity_date=date(2026, 6, 1),
        days_after=2,
        today=date(2026, 6, 7),
    )

    assert item["done"] is True
    assert item["detail"] is None


def test_activity_photo_checklist_marks_required_after_threshold():
    item = build_activity_photo_checklist_item(
        photo_count=0,
        activity_date=date(2026, 6, 1),
        days_after=2,
        today=date(2026, 6, 7),
    )

    assert item["done"] is False
    assert item["detail"] == "활동 후 2일 경과"


def test_activity_photo_checklist_not_required_before_threshold():
    item = build_activity_photo_checklist_item(
        photo_count=0,
        activity_date=date(2026, 6, 6),
        days_after=2,
        today=date(2026, 6, 7),
    )

    assert item["done"] is False
    assert item["detail"] is None
