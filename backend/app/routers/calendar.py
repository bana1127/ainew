from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.calendar import CalendarEventCreate, CalendarEventUpdate
from app.services.calendar_event_service import (
    create_calendar_event,
    event_to_calendar_item,
    list_calendar_events,
    soft_delete_calendar_event,
    update_calendar_event,
)

router = APIRouter()


@router.get("/events")
def get_calendar_events(
    year: int = Query(..., ge=1900, le=2100),
    month: int = Query(..., ge=1, le=12),
    db: Session = Depends(get_db),
) -> dict:
    return list_calendar_events(db, year=year, month=month)


@router.post("/events")
def post_calendar_event(
    payload: CalendarEventCreate,
    db: Session = Depends(get_db),
) -> dict:
    try:
        event = create_calendar_event(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return event_to_calendar_item(event)


@router.patch("/events/{event_id}")
def patch_calendar_event(
    event_id: UUID,
    payload: CalendarEventUpdate,
    db: Session = Depends(get_db),
) -> dict:
    try:
        event = update_calendar_event(db, event_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404 if "not found" in str(exc).lower() else 400, detail=str(exc))
    return event_to_calendar_item(event)


@router.delete("/events/{event_id}")
def delete_calendar_event(
    event_id: UUID,
    db: Session = Depends(get_db),
) -> dict:
    try:
        event = soft_delete_calendar_event(db, event_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"ok": True, "deleted_id": str(event.id)}
