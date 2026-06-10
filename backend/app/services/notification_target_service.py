from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import (
    ActivityParticipant,
    ActivityReport,
    BankTransaction,
    CalendarEvent,
    Member,
    NotificationDeliveryLog,
    NotificationRule,
    PaymentRecord,
    Receipt,
)
from app.services.quarter_service import quarter_date_range_from_str
from app.services.term_service import get_current_term


DEFAULT_STATUSES = ("unpaid", "partial", "need_check")


@dataclass
class NotificationTarget:
    target_type: str
    target_id: str
    recipient_email: str
    recipient_name: str | None
    subject: str
    body: str
    target_url: str | None
    reason: str


class _SafeFormat(dict):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def get_targets_for_rule(db: Session, rule: NotificationRule) -> list[NotificationTarget]:
    if not rule.enabled or rule.deleted_at is not None:
        return []

    calculators = {
        "membership_fee_due": get_membership_fee_due_targets,
        "activity_fee_due": get_activity_fee_due_targets,
        "activity_evidence_missing": get_activity_evidence_missing_targets,
        "evidence_missing": get_evidence_missing_targets,
        "activity_photo_missing": get_activity_photo_missing_targets,
        "activity_report_missing": get_activity_report_missing_targets,
        "activity_upcoming": get_activity_upcoming_targets,
        "report_missing": get_report_missing_targets,
        "calendar_deadline": get_calendar_deadline_targets,
        "quarter_settlement": get_evidence_missing_targets,
        "custom": get_custom_targets,
    }
    return calculators.get(rule.reminder_type, get_custom_targets)(db, rule)


def get_membership_fee_due_targets(
    db: Session,
    rule: NotificationRule,
) -> list[NotificationTarget]:
    conditions = rule.conditions or {}
    statuses = tuple(conditions.get("include_statuses") or DEFAULT_STATUSES)
    term = rule.term or get_current_term()
    statement = (
        select(PaymentRecord, Member)
        .join(Member, PaymentRecord.member_id == Member.id)
        .where(
            PaymentRecord.payment_type == "membership_fee",
            PaymentRecord.period == term,
            PaymentRecord.status.in_(statuses),
            Member.email.isnot(None),
        )
    )
    if conditions.get("exclude_executives"):
        statement = statement.where(Member.is_executive.is_(False))

    targets: list[NotificationTarget] = []
    for record, member in db.execute(statement):
        context = {
            "rule_name": rule.name,
            "recipient_name": member.name,
            "member_name": member.name,
            "period": term,
            "required_amount": record.required_amount,
            "paid_amount": record.paid_amount,
            "status": record.status,
            "target_url": "/payments",
        }
        target = _build_target(rule, "member", record.id, member.email, member.name, context)
        if target and _is_allowed_by_delivery_limits(db, rule, target):
            targets.append(target)
    return targets


def get_activity_fee_due_targets(
    db: Session,
    rule: NotificationRule,
) -> list[NotificationTarget]:
    conditions = rule.conditions or {}
    statuses = tuple(conditions.get("include_statuses") or DEFAULT_STATUSES)
    statement = (
        select(PaymentRecord, Member, ActivityReport)
        .join(Member, PaymentRecord.member_id == Member.id)
        .join(ActivityReport, PaymentRecord.activity_report_id == ActivityReport.id)
        .where(
            PaymentRecord.payment_type == "activity_fee",
            PaymentRecord.status.in_(statuses),
            PaymentRecord.activity_report_id.isnot(None),
            Member.email.isnot(None),
            ActivityReport.deleted_at.is_(None),
        )
    )
    if rule.activity_id:
        statement = statement.where(PaymentRecord.activity_report_id == rule.activity_id)

    targets: list[NotificationTarget] = []
    for record, member, activity in db.execute(statement):
        if conditions.get("exclude_cancelled", True) and _is_cancelled_participant(
            db,
            activity.id,
            member.id,
        ):
            continue
        target_url = f"/activities/{activity.id}?tab=activity-fee"
        context = {
            "rule_name": rule.name,
            "recipient_name": member.name,
            "member_name": member.name,
            "activity_title": activity.title,
            "activity_date": activity.activity_date,
            "required_amount": record.required_amount,
            "paid_amount": record.paid_amount,
            "status": record.status,
            "target_url": target_url,
        }
        target = _build_target(rule, "activity_fee", record.id, member.email, member.name, context)
        if target and _is_allowed_by_delivery_limits(db, rule, target):
            targets.append(target)
    return targets


def get_evidence_missing_targets(
    db: Session,
    rule: NotificationRule,
) -> list[NotificationTarget]:
    recipient = _fallback_recipient(db, rule)
    if recipient is None:
        return []

    quarter = rule.quarter
    statement = select(BankTransaction).where(
        BankTransaction.withdraw_amount > 0,
        BankTransaction.exclude_from_budget.is_(False),
    )
    if quarter:
        start, end = quarter_date_range_from_str(quarter)
        statement = statement.where(
            func.date(BankTransaction.transaction_datetime) >= start,
            func.date(BankTransaction.transaction_datetime) <= end,
        )

    targets: list[NotificationTarget] = []
    for transaction in db.scalars(statement):
        has_receipt = db.scalar(
            select(func.count(Receipt.id)).where(
                Receipt.transaction_id == transaction.id,
                Receipt.document_type != "activity_photo",
            )
        )
        if has_receipt:
            continue
        target_url = (
            f"/activities/{transaction.linked_activity_id}?tab=evidence"
            if transaction.linked_activity_id
            else "/budget"
        )
        context = {
            "rule_name": rule.name,
            "recipient_name": recipient[1],
            "quarter": quarter or "",
            "memo": transaction.memo or "",
            "amount": transaction.withdraw_amount,
            "target_url": target_url,
        }
        target = _build_target(
            rule,
            "transaction",
            transaction.id,
            recipient[0],
            recipient[1],
            context,
            reason=f"{quarter or '전체'} 기준 지출 거래에 연결된 증빙 없음",
        )
        if target and _is_allowed_by_delivery_limits(db, rule, target):
            targets.append(target)
    return targets


def get_activity_photo_missing_targets(
    db: Session,
    rule: NotificationRule,
) -> list[NotificationTarget]:
    recipient = _fallback_recipient(db, rule)
    if recipient is None:
        return []

    days_after = rule.days_after if rule.days_after is not None else 2
    cutoff = date.today() - timedelta(days=days_after)
    statement = select(ActivityReport).where(
        ActivityReport.deleted_at.is_(None),
        ActivityReport.activity_date.isnot(None),
        ActivityReport.activity_date <= cutoff,
    )
    if rule.activity_id:
        statement = statement.where(ActivityReport.id == rule.activity_id)

    targets: list[NotificationTarget] = []
    for activity in db.scalars(statement):
        has_photo = db.scalar(
            select(func.count(Receipt.id)).where(
                Receipt.activity_report_id == activity.id,
                Receipt.document_type == "activity_photo",
            )
        )
        if has_photo:
            continue
        target_url = f"/activities/{activity.id}?tab=evidence"
        context = {
            "rule_name": rule.name,
            "recipient_name": recipient[1],
            "activity_title": activity.title,
            "activity_date": activity.activity_date,
            "location": getattr(activity, "location", None) or "",
            "days_after": days_after,
            "target_url": target_url,
        }
        target = _build_target(
            rule,
            "activity",
            activity.id,
            recipient[0],
            recipient[1],
            context,
            reason=f"활동일 후 {days_after}일 경과, 활동 사진 없음",
        )
        if target and _is_allowed_by_delivery_limits(db, rule, target):
            targets.append(target)
    return targets


def get_activity_upcoming_targets(
    db: Session,
    rule: NotificationRule,
) -> list[NotificationTarget]:
    recipient = _fallback_recipient(db, rule)
    if recipient is None:
        return []

    days_before = rule.days_before if rule.days_before is not None else 1
    target_date = date.today() + timedelta(days=days_before)
    statement = select(ActivityReport).where(
        ActivityReport.deleted_at.is_(None),
        ActivityReport.activity_date.isnot(None),
        ActivityReport.activity_date == target_date,
        ActivityReport.status.notin_(("cancelled", "canceled", "deleted", "취소", "삭제")),
    )
    if rule.activity_id:
        statement = statement.where(ActivityReport.id == rule.activity_id)

    targets: list[NotificationTarget] = []
    for activity in db.scalars(statement):
        target_url = f"/activities/{activity.id}"
        context = {
            "rule_name": rule.name,
            "recipient_name": recipient[1],
            "activity_title": activity.title,
            "activity_date": activity.activity_date,
            "location": getattr(activity, "location", None) or "",
            "days_before": days_before,
            "target_url": target_url,
        }
        target = _build_target(
            rule,
            "activity",
            activity.id,
            recipient[0],
            recipient[1],
            context,
            reason=f"활동일 {days_before}일 전 알림 대상",
        )
        if target and _is_allowed_by_delivery_limits(db, rule, target):
            targets.append(target)
    return targets


def get_activity_report_missing_targets(
    db: Session,
    rule: NotificationRule,
) -> list[NotificationTarget]:
    recipient = _fallback_recipient(db, rule)
    if recipient is None:
        return []

    days_after = rule.days_after if rule.days_after is not None else 2
    cutoff = date.today() - timedelta(days=days_after)
    statement = select(ActivityReport).where(
        ActivityReport.deleted_at.is_(None),
        ActivityReport.activity_date.isnot(None),
        ActivityReport.activity_date <= cutoff,
        or_(ActivityReport.final_content.is_(None), ActivityReport.final_content == ""),
    )
    if rule.activity_id:
        statement = statement.where(ActivityReport.id == rule.activity_id)

    targets: list[NotificationTarget] = []
    for activity in db.scalars(statement):
        target_url = f"/activities/{activity.id}?tab=report"
        context = {
            "rule_name": rule.name,
            "recipient_name": recipient[1],
            "activity_title": activity.title,
            "activity_date": activity.activity_date,
            "location": getattr(activity, "location", None) or "",
            "days_after": days_after,
            "target_url": target_url,
        }
        target = _build_target(
            rule,
            "activity",
            activity.id,
            recipient[0],
            recipient[1],
            context,
            reason=f"활동일 후 {days_after}일 경과, 보고서 미작성",
        )
        if target and _is_allowed_by_delivery_limits(db, rule, target):
            targets.append(target)
    return targets


def get_activity_evidence_missing_targets(
    db: Session,
    rule: NotificationRule,
) -> list[NotificationTarget]:
    recipient = _fallback_recipient(db, rule)
    if recipient is None:
        return []

    days_after = rule.days_after if rule.days_after is not None else 2
    cutoff = date.today() - timedelta(days=days_after)
    statement = select(ActivityReport).where(
        ActivityReport.deleted_at.is_(None),
        ActivityReport.activity_date.isnot(None),
        ActivityReport.activity_date <= cutoff,
    )
    if rule.activity_id:
        statement = statement.where(ActivityReport.id == rule.activity_id)

    targets: list[NotificationTarget] = []
    for activity in db.scalars(statement):
        has_evidence = db.scalar(
            select(func.count(Receipt.id)).where(
                Receipt.activity_report_id == activity.id,
                Receipt.document_type != "activity_photo",
            )
        )
        if has_evidence:
            continue
        target_url = f"/activities/{activity.id}?tab=evidence"
        context = {
            "rule_name": rule.name,
            "recipient_name": recipient[1],
            "activity_title": activity.title,
            "activity_date": activity.activity_date,
            "location": getattr(activity, "location", None) or "",
            "days_after": days_after,
            "target_url": target_url,
        }
        target = _build_target(
            rule,
            "activity",
            activity.id,
            recipient[0],
            recipient[1],
            context,
            reason=f"활동일 후 {days_after}일 경과, 활동 증빙 없음",
        )
        if target and _is_allowed_by_delivery_limits(db, rule, target):
            targets.append(target)
    return targets


def get_report_missing_targets(db: Session, rule: NotificationRule) -> list[NotificationTarget]:
    recipient = _fallback_recipient(db, rule)
    if recipient is None:
        return []
    days_after = rule.days_after if rule.days_after is not None else 0
    cutoff = date.today() - timedelta(days=days_after)
    statement = select(ActivityReport).where(
        ActivityReport.deleted_at.is_(None),
        ActivityReport.activity_date.isnot(None),
        ActivityReport.activity_date <= cutoff,
        ActivityReport.final_content.is_(None),
    )
    targets: list[NotificationTarget] = []
    for activity in db.scalars(statement):
        target_url = f"/activities/{activity.id}?tab=report"
        context = {
            "rule_name": rule.name,
            "recipient_name": recipient[1],
            "activity_title": activity.title,
            "activity_date": activity.activity_date,
            "target_url": target_url,
        }
        target = _build_target(rule, "activity", activity.id, recipient[0], recipient[1], context)
        if target and _is_allowed_by_delivery_limits(db, rule, target):
            targets.append(target)
    return targets


def get_calendar_deadline_targets(
    db: Session,
    rule: NotificationRule,
) -> list[NotificationTarget]:
    recipient = _fallback_recipient(db, rule)
    if recipient is None:
        return []
    days_before = rule.days_before if rule.days_before is not None else 0
    target_date = date.today() + timedelta(days=days_before)
    event_types = tuple((rule.conditions or {}).get("event_types") or ("deadline", "meeting", "general"))
    statement = select(CalendarEvent).where(
        CalendarEvent.deleted_at.is_(None),
        CalendarEvent.event_type.in_(event_types),
        CalendarEvent.event_date == target_date,
    )

    targets: list[NotificationTarget] = []
    for event in db.scalars(statement):
        target_url = (
            f"/activities/{event.activity_report_id}"
            if event.activity_report_id
            else "/dashboard"
        )
        context = {
            "rule_name": rule.name,
            "recipient_name": recipient[1],
            "event_title": event.title,
            "event_type": event.event_type,
            "event_date": event.event_date,
            "target_url": target_url,
        }
        target = _build_target(
            rule,
            "calendar_event",
            event.id,
            recipient[0],
            recipient[1],
            context,
            reason=f"calendar event 기준 {days_before}일 전 알림",
        )
        if target and _is_allowed_by_delivery_limits(db, rule, target):
            targets.append(target)
    return targets


def get_custom_targets(db: Session, rule: NotificationRule) -> list[NotificationTarget]:
    recipient = _fallback_recipient(db, rule)
    if recipient is None:
        return []
    context = {
        "rule_name": rule.name,
        "recipient_name": recipient[1],
        "target_url": (rule.conditions or {}).get("target_url") or "/notifications",
    }
    target = _build_target(rule, "custom", str(rule.id), recipient[0], recipient[1], context)
    if target and _is_allowed_by_delivery_limits(db, rule, target):
        return [target]
    return []


def _build_target(
    rule: NotificationRule,
    target_type: str,
    target_id: UUID | str,
    recipient_email: str | None,
    recipient_name: str | None,
    context: dict[str, Any],
    reason: str | None = None,
) -> NotificationTarget | None:
    if not recipient_email:
        return None
    subject = _render(rule.template_subject, context)
    body = _render(rule.template_body, context)
    target_url = str(context.get("target_url") or "")
    return NotificationTarget(
        target_type=target_type,
        target_id=str(target_id),
        recipient_email=recipient_email,
        recipient_name=recipient_name,
        subject=subject,
        body=body,
        target_url=target_url or None,
        reason=reason or _default_reason(rule),
    )


def _render(template: str, context: dict[str, Any]) -> str:
    normalized = template.replace("{{", "{").replace("}}", "}")
    return normalized.format_map(
        _SafeFormat({k: "" if v is None else v for k, v in context.items()})
    )


def _default_reason(rule: NotificationRule) -> str:
    scope = {
        "membership_fee_due": "학기 기준 회비 상태",
        "activity_fee_due": "활동 기준 활동비 상태",
        "evidence_missing": "분기 기준 증빙 누락",
        "activity_photo_missing": "활동일 기준 활동 사진 누락",
        "activity_report_missing": "활동일 기준 보고서 누락",
        "activity_evidence_missing": "활동일 기준 활동 증빙 누락",
        "activity_upcoming": "활동일 기준 활동 전 알림",
        "calendar_deadline": "calendar event 기준 일정",
    }.get(rule.reminder_type, "사용자 설정 조건")
    return f"{scope}에 해당"


def _is_cancelled_participant(db: Session, activity_id: UUID, member_id: UUID) -> bool:
    participant = db.scalar(
        select(ActivityParticipant).where(
            ActivityParticipant.activity_report_id == activity_id,
            ActivityParticipant.member_id == member_id,
        )
    )
    status = (participant.status or "").lower() if participant else ""
    return status in {"cancelled", "canceled", "excluded", "취소", "제외"}


def _fallback_recipient(db: Session, rule: NotificationRule) -> tuple[str, str | None] | None:
    conditions = rule.conditions or {}
    email = conditions.get("recipient_email")
    if email:
        return str(email), conditions.get("recipient_name") or "운영진"

    member = db.scalar(
        select(Member)
        .where(Member.email.isnot(None), Member.is_executive.is_(True))
        .order_by(Member.created_at)
    )
    if member and member.email:
        return member.email, member.name

    member = db.scalar(select(Member).where(Member.email.isnot(None)).order_by(Member.created_at))
    if member and member.email:
        return member.email, member.name
    return None


def _is_allowed_by_delivery_limits(
    db: Session,
    rule: NotificationRule,
    target: NotificationTarget,
) -> bool:
    sent_statuses = ("pending", "sent")
    count = db.scalar(
        select(func.count(NotificationDeliveryLog.id)).where(
            NotificationDeliveryLog.rule_id == rule.id,
            NotificationDeliveryLog.target_type == target.target_type,
            NotificationDeliveryLog.target_id == target.target_id,
            NotificationDeliveryLog.recipient_email == target.recipient_email,
            NotificationDeliveryLog.status.in_(sent_statuses),
        )
    ) or 0
    if rule.max_send_count is not None and count >= rule.max_send_count:
        return False

    if rule.repeat_interval_days:
        since = datetime.now(timezone.utc) - timedelta(days=rule.repeat_interval_days)
        recent = db.scalar(
            select(func.count(NotificationDeliveryLog.id)).where(
                NotificationDeliveryLog.rule_id == rule.id,
                NotificationDeliveryLog.target_type == target.target_type,
                NotificationDeliveryLog.target_id == target.target_id,
                NotificationDeliveryLog.recipient_email == target.recipient_email,
                NotificationDeliveryLog.status.in_(sent_statuses),
                NotificationDeliveryLog.created_at >= since,
            )
        ) or 0
        if recent:
            return False
    return True


def absolute_target_url(target_url: str | None) -> str | None:
    if not target_url:
        return None
    if target_url.startswith("http://") or target_url.startswith("https://"):
        return target_url
    base = settings.FRONTEND_URL.rstrip("/")
    return f"{base}{target_url}" if base else target_url
