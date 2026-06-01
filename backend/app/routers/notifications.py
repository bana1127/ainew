from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Notification
from app.routers.common import apply_updates, commit_or_400, get_or_404
from app.schemas import NotificationCreate, NotificationRead, NotificationUpdate


router = APIRouter()


@router.get("", response_model=list[NotificationRead])
def list_notifications(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    is_read: bool | None = None,
    type: str | None = None,
    severity: str | None = None,
    db: Session = Depends(get_db),
) -> list[Notification]:
    statement = select(Notification)
    if is_read is not None:
        statement = statement.where(Notification.is_read.is_(is_read))
    if type:
        statement = statement.where(Notification.type == type)
    if severity:
        statement = statement.where(Notification.severity == severity)
    return list(db.scalars(statement.offset(skip).limit(limit)))


@router.post("", response_model=NotificationRead)
def create_notification(
    payload: NotificationCreate,
    db: Session = Depends(get_db),
) -> Notification:
    notification = Notification(**payload.model_dump())
    db.add(notification)
    commit_or_400(db, "Could not create notification")
    db.refresh(notification)
    return notification


@router.patch("/read-all")
def read_all_notifications(db: Session = Depends(get_db)) -> dict[str, int]:
    result = db.execute(
        update(Notification).where(Notification.is_read.is_(False)).values(is_read=True)
    )
    db.commit()
    return {"updated": result.rowcount or 0}


@router.get("/{notification_id}", response_model=NotificationRead)
def get_notification(
    notification_id: UUID,
    db: Session = Depends(get_db),
) -> Notification:
    return get_or_404(db, Notification, notification_id, "Notification")


@router.patch("/{notification_id}", response_model=NotificationRead)
def update_notification(
    notification_id: UUID,
    payload: NotificationUpdate,
    db: Session = Depends(get_db),
) -> Notification:
    notification = get_or_404(db, Notification, notification_id, "Notification")
    apply_updates(notification, payload)
    commit_or_400(db, "Could not update notification")
    db.refresh(notification)
    return notification


@router.patch("/{notification_id}/read", response_model=NotificationRead)
def read_notification(
    notification_id: UUID,
    db: Session = Depends(get_db),
) -> Notification:
    notification = get_or_404(db, Notification, notification_id, "Notification")
    notification.is_read = True
    commit_or_400(db, "Could not mark notification as read")
    db.refresh(notification)
    return notification


@router.delete("/{notification_id}", response_model=NotificationRead)
def delete_notification(
    notification_id: UUID,
    db: Session = Depends(get_db),
) -> Notification:
    notification = get_or_404(db, Notification, notification_id, "Notification")
    db.delete(notification)
    commit_or_400(db, "Could not delete notification")
    return notification

