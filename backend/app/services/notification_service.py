from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import NotificationDeliveryLog, NotificationRule
from app.schemas.notification import (
    NotificationDeliveryLogCreate,
    NotificationPreviewItem,
    NotificationPreviewResponse,
)
from app.services import n8n_service
from app.services.n8n_service import N8nServiceError
from app.services.notification_target_service import (
    NotificationTarget,
    absolute_target_url,
    get_targets_for_rule,
)


def preview_rule(db: Session, rule_id: UUID) -> NotificationPreviewResponse:
    rule = _get_active_rule(db, rule_id)
    targets = get_targets_for_rule(db, rule)
    return NotificationPreviewResponse(
        rule_id=rule.id,
        count=len(targets),
        items=[_target_to_schema(target, rule) for target in targets],
    )


def get_due_notifications(db: Session) -> list[NotificationPreviewItem]:
    rules = list(
        db.scalars(
            select(NotificationRule).where(
                NotificationRule.enabled.is_(True),
                NotificationRule.deleted_at.is_(None),
            )
        )
    )
    items: list[NotificationPreviewItem] = []
    for rule in rules:
        items.extend(_target_to_schema(target, rule) for target in get_targets_for_rule(db, rule))
    return items


def send_rule_now(db: Session, rule_id: UUID) -> list[NotificationDeliveryLog]:
    rule = _get_active_rule(db, rule_id)
    logs: list[NotificationDeliveryLog] = []
    for target in get_targets_for_rule(db, rule):
        log = NotificationDeliveryLog(
            rule_id=rule.id,
            reminder_type=rule.reminder_type,
            target_type=target.target_type,
            target_id=target.target_id,
            recipient_email=target.recipient_email,
            recipient_name=target.recipient_name,
            subject=target.subject,
            body=target.body,
            target_url=target.target_url,
            provider="n8n",
            status="pending",
        )
        db.add(log)
        db.flush()
        try:
            result = n8n_service.send_notification_email(
                {
                    "delivery_log_id": str(log.id),
                    "rule_id": str(rule.id),
                    "reminder_type": rule.reminder_type,
                    "target_type": target.target_type,
                    "target_id": target.target_id,
                    "recipient_email": target.recipient_email,
                    "recipient_name": target.recipient_name,
                    "subject": target.subject,
                    "body": target.body,
                    "target_url": absolute_target_url(target.target_url),
                }
            )
        except N8nServiceError as exc:
            log.status = "failed"
            log.error_message = str(exc)
        else:
            log.status = "sent"
            log.sent_at = datetime.now(timezone.utc)
            if isinstance(result, dict):
                provider_id = result.get("message_id") or result.get("id")
                log.provider_message_id = str(provider_id) if provider_id else None
        logs.append(log)
    db.commit()
    for log in logs:
        db.refresh(log)
    return logs


def log_delivery_result(
    db: Session,
    payload: NotificationDeliveryLogCreate,
) -> NotificationDeliveryLog:
    log = None
    if payload.provider_message_id:
        log = db.scalar(
            select(NotificationDeliveryLog).where(
                NotificationDeliveryLog.provider_message_id == payload.provider_message_id
            )
        )
    if log is None:
        log = NotificationDeliveryLog(**payload.model_dump())
        db.add(log)
    else:
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(log, key, value)
    if payload.status == "sent" and log.sent_at is None:
        log.sent_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(log)
    return log


def _get_active_rule(db: Session, rule_id: UUID) -> NotificationRule:
    rule = db.get(NotificationRule, rule_id)
    if not rule or rule.deleted_at is not None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="NotificationRule not found")
    return rule


def _target_to_schema(
    target: NotificationTarget,
    rule: NotificationRule | None = None,
) -> NotificationPreviewItem:
    return NotificationPreviewItem(
        rule_id=rule.id if rule else None,
        reminder_type=rule.reminder_type if rule else None,
        target_type=target.target_type,
        target_id=target.target_id,
        recipient_email=target.recipient_email,
        recipient_name=target.recipient_name,
        subject=target.subject,
        body=target.body,
        target_url=target.target_url,
        reason=target.reason,
    )
