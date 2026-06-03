"""Settlement service for activity fee overpayment/refund management.

Status values:
  payment status: unpaid | partial | paid | overpaid | need_check | exempt | refunded | cancelled
  refund_status:  none | refund_required | refund_pending | refunded | refund_denied
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.models.payment import PaymentAdjustmentLog, PaymentRecord


# ── Status recalculation ───────────────────────────────────────────────────────

def recalculate_payment_status(db: Session, record: PaymentRecord) -> str:
    """Recalculate and update payment status based on amounts.

    Returns the new status.
    """
    paid = record.paid_amount or 0
    required = record.required_amount or 0

    if record.status in ("exempt", "cancelled"):
        return record.status

    if paid == 0:
        new_status = "unpaid"
    elif paid < required:
        new_status = "partial"
    elif paid == required:
        new_status = "paid"
    else:
        new_status = "overpaid"

    if new_status != record.status:
        record.status = new_status
        db.flush()
    return new_status


def compute_overpaid_amount(record: PaymentRecord) -> int:
    """Return the overpaid amount (0 if not overpaid)."""
    paid = record.paid_amount or 0
    required = record.required_amount or 0
    return max(0, paid - required)


def detect_refund_required_for_record(
    db: Session,
    record: PaymentRecord,
) -> bool:
    """Return True if this record should be marked refund_required.

    Conditions:
      1. overpaid (paid_amount > required_amount), or
      2. participant status is cancelled/no_show and paid_amount > 0
    """
    from sqlalchemy import and_
    from app.models.activity import ActivityParticipant

    if (record.paid_amount or 0) > (record.required_amount or 0):
        return True

    if (record.paid_amount or 0) > 0 and record.activity_report_id:
        participant = db.scalar(
            select(ActivityParticipant).where(
                and_(
                    ActivityParticipant.activity_report_id == record.activity_report_id,
                    ActivityParticipant.member_id == record.member_id,
                    ActivityParticipant.status.in_(["cancelled", "no_show"]),
                )
            )
        )
        if participant:
            return True

    return False


# ── Refund state transitions ───────────────────────────────────────────────────

def mark_refund_required(
    db: Session,
    record_id: UUID,
    refund_amount: int | None = None,
    reason: str | None = None,
) -> PaymentRecord:
    record = db.get(PaymentRecord, record_id)
    if not record:
        raise ValueError(f"PaymentRecord {record_id} not found")

    prev_refund = record.refund_status
    if refund_amount is None:
        refund_amount = compute_overpaid_amount(record) or record.paid_amount or 0
    record.refund_status = "refund_required"
    record.refund_amount = refund_amount
    if reason:
        record.refund_reason = reason

    create_adjustment_log(
        db,
        payment_record_id=record_id,
        action="refund_required",
        previous_status=prev_refund,
        new_status="refund_required",
        refund_amount=refund_amount,
        reason=reason,
    )
    db.flush()
    return record


def mark_refund_pending(
    db: Session,
    record_id: UUID,
    refund_amount: int | None = None,
    reason: str | None = None,
) -> PaymentRecord:
    record = db.get(PaymentRecord, record_id)
    if not record:
        raise ValueError(f"PaymentRecord {record_id} not found")

    prev_refund = record.refund_status
    if refund_amount is not None:
        record.refund_amount = refund_amount
    record.refund_status = "refund_pending"
    if reason:
        record.refund_reason = reason

    create_adjustment_log(
        db,
        payment_record_id=record_id,
        action="refund_pending",
        previous_status=prev_refund,
        new_status="refund_pending",
        refund_amount=record.refund_amount,
        reason=reason,
    )
    db.flush()
    return record


def mark_refunded(
    db: Session,
    record_id: UUID,
    refund_transaction_id: UUID | None = None,
    refund_amount: int | None = None,
    reason: str | None = None,
) -> PaymentRecord:
    record = db.get(PaymentRecord, record_id)
    if not record:
        raise ValueError(f"PaymentRecord {record_id} not found")

    prev_refund = record.refund_status
    prev_status = record.status

    if refund_amount is not None:
        record.refund_amount = refund_amount
    if refund_transaction_id is not None:
        record.refund_transaction_id = refund_transaction_id
    record.refund_status = "refunded"
    record.refunded_at = datetime.now(tz=timezone.utc)
    if reason:
        record.refund_reason = reason

    # Recalculate status after refund
    paid = record.paid_amount or 0
    ref = record.refund_amount or 0
    required = record.required_amount or 0
    net = paid - ref
    if net <= 0:
        record.status = "refunded"
    elif net < required:
        record.status = "partial"
    elif net >= required:
        record.status = "paid"

    create_adjustment_log(
        db,
        payment_record_id=record_id,
        transaction_id=refund_transaction_id,
        action="refund_completed",
        previous_status=f"{prev_status}/{prev_refund}",
        new_status=f"{record.status}/refunded",
        refund_amount=record.refund_amount,
        reason=reason,
    )
    db.flush()
    return record


def cancel_refund(
    db: Session,
    record_id: UUID,
    reason: str | None = None,
) -> PaymentRecord:
    record = db.get(PaymentRecord, record_id)
    if not record:
        raise ValueError(f"PaymentRecord {record_id} not found")

    prev_refund = record.refund_status
    record.refund_status = "none"
    record.refund_transaction_id = None
    record.refunded_at = None
    if reason:
        record.refund_reason = reason

    # Recalculate status
    recalculate_payment_status(db, record)

    create_adjustment_log(
        db,
        payment_record_id=record_id,
        action="refund_cancelled",
        previous_status=prev_refund,
        new_status="none",
        reason=reason,
    )
    db.flush()
    return record


# ── Log creation ───────────────────────────────────────────────────────────────

def create_adjustment_log(
    db: Session,
    payment_record_id: UUID,
    action: str,
    transaction_id: UUID | None = None,
    previous_status: str | None = None,
    new_status: str | None = None,
    previous_paid_amount: int | None = None,
    new_paid_amount: int | None = None,
    refund_amount: int | None = None,
    reason: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> PaymentAdjustmentLog:
    log = PaymentAdjustmentLog(
        payment_record_id=payment_record_id,
        transaction_id=transaction_id,
        action=action,
        previous_status=previous_status,
        new_status=new_status,
        previous_paid_amount=previous_paid_amount,
        new_paid_amount=new_paid_amount,
        refund_amount=refund_amount,
        reason=reason,
        metadata_json=metadata,
    )
    db.add(log)
    return log


# ── Bulk detection ─────────────────────────────────────────────────────────────

def detect_refund_required(
    db: Session,
    activity_id: UUID | None = None,
) -> list[PaymentRecord]:
    """Return all payment records that should be refund_required but aren't."""
    stmt = select(PaymentRecord).where(
        PaymentRecord.payment_type == "activity_fee",
        PaymentRecord.refund_status.notin_(["refunded", "refund_denied"]),
    )
    if activity_id:
        stmt = stmt.where(PaymentRecord.activity_report_id == activity_id)

    records = list(db.scalars(stmt))
    result = []
    for r in records:
        if detect_refund_required_for_record(db, r):
            result.append(r)
    return result
