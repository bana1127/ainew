from __future__ import annotations

import os
from datetime import date
from types import SimpleNamespace
from uuid import uuid4

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from app.schemas.calendar import CalendarEventCreate
from app.services import calendar_event_service as svc


class _FakeEvent:
    def __init__(self, **kwargs):
        self.id = uuid4()
        self.created_at = None
        self.updated_at = None
        self.deleted_at = None
        for key, value in kwargs.items():
            setattr(self, key, value)


class _FakeDb:
    def __init__(self):
        self.added = []
        self.committed = False

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.committed = True

    def refresh(self, obj):
        return None


def test_general_event_create_does_not_create_activity_report(monkeypatch):
    monkeypatch.setattr(svc, "CalendarEvent", _FakeEvent)
    db = _FakeDb()

    event = svc.create_calendar_event(
        db,
        CalendarEventCreate(
            title="회비 납부 마감",
            event_type="deadline",
            event_date=date(2026, 6, 10),
        ),
    )

    assert len(db.added) == 1
    assert event.event_type == "deadline"
    assert getattr(event, "activity_report_id", None) is None
    assert db.committed is True


def test_activity_type_cannot_be_created_as_general_event(monkeypatch):
    monkeypatch.setattr(svc, "CalendarEvent", _FakeEvent)
    db = _FakeDb()

    try:
        svc.create_calendar_event(
            db,
            CalendarEventCreate(
                title="활동처럼 보이는 일정",
                event_type="activity",
                event_date=date(2026, 6, 10),
            ),
        )
    except ValueError as exc:
        assert "activity" in str(exc)
    else:
        raise AssertionError("activity type must be rejected")


def test_event_to_calendar_item_has_null_activity_link():
    event = _FakeEvent(
        title="운영진 회의",
        event_type="meeting",
        event_date=date(2026, 6, 4),
        start_time=None,
        end_time=None,
        location="A401",
        description="안건 정리",
        status="planned",
        activity_report_id=None,
        is_all_day=True,
    )

    item = svc.event_to_calendar_item(event)

    assert item["event_type"] == "meeting"
    assert item["date"] == "2026-06-04"
    assert item["activity_report_id"] is None
    assert item["target_url"] is None


def test_activity_to_calendar_item_links_to_activity_detail():
    activity_id = uuid4()
    activity = SimpleNamespace(
        id=activity_id,
        title="위퍼퓸 교내조향활동",
        activity_date=date(2026, 6, 3),
        location="A401",
        status="planned",
        created_at=None,
        updated_at=None,
    )

    item = svc.activity_to_calendar_item(activity)

    assert item["event_type"] == "activity"
    assert item["activity_report_id"] == str(activity_id)
    assert item["target_url"] == f"/activities/{activity_id}"
