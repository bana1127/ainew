from uuid import UUID

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Notification, NotificationDeliveryLog, NotificationRule
from app.routers.common import apply_updates, commit_or_400, get_or_404
from app.schemas import (
    NotificationCreate,
    NotificationDeliveryLogCreate,
    NotificationDeliveryLogRead,
    NotificationDueResponse,
    NotificationPreviewResponse,
    NotificationRead,
    NotificationRuleCreate,
    NotificationRuleRead,
    NotificationRuleUpdate,
    NotificationSendResult,
    NotificationUpdate,
)
from app.services import notification_service


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


@router.get("/rules", response_model=list[NotificationRuleRead])
def list_notification_rules(
    include_disabled: bool = True,
    db: Session = Depends(get_db),
) -> list[NotificationRule]:
    statement = select(NotificationRule).where(NotificationRule.deleted_at.is_(None))
    if not include_disabled:
        statement = statement.where(NotificationRule.enabled.is_(True))
    return list(db.scalars(statement.order_by(NotificationRule.created_at.desc())))


@router.post("/rules", response_model=NotificationRuleRead)
def create_notification_rule(
    payload: NotificationRuleCreate,
    db: Session = Depends(get_db),
) -> NotificationRule:
    rule = NotificationRule(**payload.model_dump())
    db.add(rule)
    commit_or_400(db, "Could not create notification rule")
    db.refresh(rule)
    return rule


@router.get("/rules/{rule_id}", response_model=NotificationRuleRead)
def get_notification_rule(
    rule_id: UUID,
    db: Session = Depends(get_db),
) -> NotificationRule:
    return get_or_404(db, NotificationRule, rule_id, "NotificationRule")


@router.patch("/rules/{rule_id}", response_model=NotificationRuleRead)
def update_notification_rule(
    rule_id: UUID,
    payload: NotificationRuleUpdate,
    db: Session = Depends(get_db),
) -> NotificationRule:
    rule = get_or_404(db, NotificationRule, rule_id, "NotificationRule")
    apply_updates(rule, payload)
    commit_or_400(db, "Could not update notification rule")
    db.refresh(rule)
    return rule


@router.delete("/rules/{rule_id}", response_model=NotificationRuleRead)
def delete_notification_rule(
    rule_id: UUID,
    db: Session = Depends(get_db),
) -> NotificationRule:
    rule = get_or_404(db, NotificationRule, rule_id, "NotificationRule")
    rule.enabled = False
    rule.deleted_at = datetime.now(timezone.utc)
    commit_or_400(db, "Could not delete notification rule")
    db.refresh(rule)
    return rule


@router.post("/rules/{rule_id}/preview", response_model=NotificationPreviewResponse)
def preview_notification_rule(
    rule_id: UUID,
    db: Session = Depends(get_db),
) -> NotificationPreviewResponse:
    return notification_service.preview_rule(db, rule_id)


@router.post("/rules/{rule_id}/send-now", response_model=NotificationSendResult)
def send_notification_rule_now(
    rule_id: UUID,
    db: Session = Depends(get_db),
) -> NotificationSendResult:
    logs = notification_service.send_rule_now(db, rule_id)
    return NotificationSendResult(
        requested=len(logs),
        sent=sum(1 for log in logs if log.status == "sent"),
        failed=sum(1 for log in logs if log.status == "failed"),
        skipped=sum(1 for log in logs if log.status == "skipped"),
        logs=[NotificationDeliveryLogRead.model_validate(log) for log in logs],
    )


@router.get("/due", response_model=NotificationDueResponse)
def get_due_notifications(db: Session = Depends(get_db)) -> NotificationDueResponse:
    items = notification_service.get_due_notifications(db)
    return NotificationDueResponse(count=len(items), items=items)


@router.get("/logs", response_model=list[NotificationDeliveryLogRead])
def list_delivery_logs(
    rule_id: UUID | None = None,
    status: str | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=300),
    db: Session = Depends(get_db),
) -> list[NotificationDeliveryLog]:
    statement = select(NotificationDeliveryLog)
    if rule_id:
        statement = statement.where(NotificationDeliveryLog.rule_id == rule_id)
    if status:
        statement = statement.where(NotificationDeliveryLog.status == status)
    return list(
        db.scalars(
            statement.order_by(NotificationDeliveryLog.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
    )


@router.post("/log", response_model=NotificationDeliveryLogRead)
def create_delivery_log(
    payload: NotificationDeliveryLogCreate,
    db: Session = Depends(get_db),
) -> NotificationDeliveryLog:
    return notification_service.log_delivery_result(db, payload)


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
