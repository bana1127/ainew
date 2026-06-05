from __future__ import annotations

import calendar
from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.models import ActivityReport, CalendarEvent
from app.schemas.calendar import CalendarEventCreate, CalendarEventUpdate

GENERAL_EVENT_TYPES = {"general", "deadline", "meeting"}
ALL_EVENT_TYPES = {"activity", *GENERAL_EVENT_TYPES}


def month_range(year: int, month: int) -> tuple[date, date]:
    _, last_day = calendar.monthrange(year, month)
    return date(year, month, 1), date(year, month, last_day)


def _iso_time(value) -> str | None:
    return value.isoformat(timespec="minutes") if value else None


def activity_to_calendar_item(activity: ActivityReport) -> dict:
    return {
        "id": f"activity-{activity.id}",
        "event_type": "activity",
        "title": activity.title or "(제목 없음)",
        "date": activity.activity_date.isoformat() if activity.activity_date else None,
        "start_time": None,
        "end_time": None,
        "location": activity.location,
        "description": None,
        "status": activity.status or "planned",
        "activity_report_id": str(activity.id),
        "target_url": f"/activities/{activity.id}",
        "is_all_day": True,
        "created_at": activity.created_at,
        "updated_at": activity.updated_at,
    }


def event_to_calendar_item(event: CalendarEvent) -> dict:
    return {
        "id": str(event.id),
        "event_type": event.event_type,
        "title": event.title,
        "date": event.event_date.isoformat(),
        "start_time": _iso_time(event.start_time),
        "end_time": _iso_time(event.end_time),
        "location": event.location,
        "description": event.description,
        "status": event.status,
        "activity_report_id": str(event.activity_report_id) if event.activity_report_id else None,
        "target_url": f"/activities/{event.activity_report_id}" if event.event_type == "activity" and event.activity_report_id else None,
        "is_all_day": bool(event.is_all_day),
        "created_at": event.created_at,
        "updated_at": event.updated_at,
    }


def list_calendar_events(db: Session, *, year: int, month: int) -> dict:
    start, end = month_range(year, month)
    activities = list(db.scalars(
        select(ActivityReport).where(
            and_(
                ActivityReport.deleted_at.is_(None),
                ActivityReport.activity_date >= start,
                ActivityReport.activity_date <= end,
            )
        )
    ))
    events = list(db.scalars(
        select(CalendarEvent).where(
            and_(
                CalendarEvent.deleted_at.is_(None),
                CalendarEvent.event_date >= start,
                CalendarEvent.event_date <= end,
            )
        )
    ))
    items = [
        *(activity_to_calendar_item(activity) for activity in activities if activity.activity_date),
        *(event_to_calendar_item(event) for event in events),
    ]
    items.sort(key=lambda item: (item["date"], item.get("start_time") or "", item["title"]))
    return {"year": year, "month": month, "items": items}


def create_calendar_event(db: Session, payload: CalendarEventCreate) -> CalendarEvent:
    if payload.event_type == "activity":
        raise ValueError("일반 일정 API에서는 activity event를 직접 생성할 수 없습니다")
    if payload.event_type not in GENERAL_EVENT_TYPES:
        raise ValueError(f"지원하지 않는 일정 유형입니다: {payload.event_type}")
    event = CalendarEvent(**payload.model_dump())
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def update_calendar_event(db: Session, event_id: UUID, payload: CalendarEventUpdate) -> CalendarEvent:
    event = db.get(CalendarEvent, event_id)
    if event is None or event.deleted_at is not None:
        raise ValueError("Calendar event not found")
    data = payload.model_dump(exclude_unset=True)
    if data.get("event_type") == "activity":
        raise ValueError("일반 일정은 activity 타입으로 변경할 수 없습니다")
    if "event_type" in data and data["event_type"] not in GENERAL_EVENT_TYPES:
        raise ValueError(f"지원하지 않는 일정 유형입니다: {data['event_type']}")
    for key, value in data.items():
        setattr(event, key, value)
    db.commit()
    db.refresh(event)
    return event


def soft_delete_calendar_event(db: Session, event_id: UUID) -> CalendarEvent:
    event = db.get(CalendarEvent, event_id)
    if event is None or event.deleted_at is not None:
        raise ValueError("Calendar event not found")
    event.deleted_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(event)
    return event
