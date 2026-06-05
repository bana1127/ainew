from __future__ import annotations

from datetime import date, datetime, time
from uuid import UUID

from pydantic import BaseModel, Field


CalendarEventType = str


class CalendarEventCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    event_type: CalendarEventType = "general"
    event_date: date
    start_time: time | None = None
    end_time: time | None = None
    location: str | None = None
    description: str | None = None
    status: str = "planned"
    activity_report_id: UUID | None = None
    is_all_day: bool = True


class CalendarEventUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    event_type: CalendarEventType | None = None
    event_date: date | None = None
    start_time: time | None = None
    end_time: time | None = None
    location: str | None = None
    description: str | None = None
    status: str | None = None
    is_all_day: bool | None = None


class CalendarEventItem(BaseModel):
    id: str
    event_type: str
    title: str
    date: str
    start_time: str | None = None
    end_time: str | None = None
    location: str | None = None
    description: str | None = None
    status: str
    activity_report_id: str | None = None
    target_url: str | None = None
    is_all_day: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CalendarEventsResponse(BaseModel):
    year: int
    month: int
    items: list[CalendarEventItem]
