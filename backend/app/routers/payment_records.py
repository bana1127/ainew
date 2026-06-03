from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import BankTransaction, Member, PaymentRecord
from app.models.activity import ActivityReport
from app.routers.common import apply_updates, commit_or_400, get_or_404
from app.schemas import PaymentRecordCreate, PaymentRecordRead, PaymentRecordUpdate
from pydantic import BaseModel


router = APIRouter()


class ManualPaymentPayload(BaseModel):
    member_id: UUID
    period: str
    payment_type: str = "membership_fee"
    required_amount: int = 0
    paid_amount: int = 0
    status: str | None = None
    manual_note: str | None = None


def _auto_status(paid: int, required: int, explicit: str | None) -> str:
    """Compute status from amounts unless user supplied a manual review state."""
    if explicit in {"need_check", "cancelled"}:
        return explicit
    if explicit == "paid" and required > 0 and paid <= 0:
        return "paid"
    if explicit == "unpaid":
        return "exempt" if required <= 0 else "unpaid"
    if explicit == "exempt":
        return "exempt"
    if required <= 0:
        return "exempt"
    if paid <= 0:
        return "unpaid"
    if paid < required:
        return "partial"
    if paid == required:
        return "paid"
    return "overpaid"


def _auto_paid_amount(status: str, paid: int, required: int) -> int:
    """Auto-fill paid_amount based on status to prevent inconsistencies."""
    if status == "paid" and paid == 0 and required > 0:
        return required
    if status in ("unpaid", "exempt"):
        return 0
    return paid


def ensure_relations(
    db: Session,
    member_id: UUID | None = None,
    transaction_id: UUID | None = None,
) -> None:
    if member_id and db.get(Member, member_id) is None:
        raise HTTPException(status_code=404, detail="Member not found")
    if transaction_id and db.get(BankTransaction, transaction_id) is None:
        raise HTTPException(status_code=404, detail="Transaction not found")


def _enrich(
    record: PaymentRecord,
    member: Member | None,
    activity: ActivityReport | None = None,
) -> PaymentRecordRead:
    """Build a PaymentRecordRead with member + activity info attached."""
    data = PaymentRecordRead.model_validate(record)
    if member:
        data.member_name = member.name
        data.student_id = member.student_id
        data.department = member.department
    if activity:
        data.activity_title = activity.title
    # Populate refund fields from model (not in base schema)
    data.refund_status = getattr(record, "refund_status", None)
    data.refund_amount = getattr(record, "refund_amount", None)
    return data


@router.get("", response_model=list[PaymentRecordRead])
def list_payment_records(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=1000, ge=1, le=10000),
    member_id: UUID | None = None,
    period: str | None = None,
    status: str | None = None,
    payment_type: str | None = None,
    db: Session = Depends(get_db),
) -> list[PaymentRecordRead]:
    statement = select(PaymentRecord)
    if member_id:
        statement = statement.where(PaymentRecord.member_id == member_id)
    if period:
        statement = statement.where(PaymentRecord.period == period)
    if status:
        statement = statement.where(PaymentRecord.status == status)
    if payment_type:
        statement = statement.where(PaymentRecord.payment_type == payment_type)
    records = list(db.scalars(statement.offset(skip).limit(limit)))

    # Bulk-load member info
    member_ids = {r.member_id for r in records}
    members_map: dict[UUID, Member] = {}
    if member_ids:
        members = db.execute(
            select(Member).where(Member.id.in_(member_ids))
        ).scalars().all()
        members_map = {m.id: m for m in members}

    # Bulk-load activity info (only for activity_fee records)
    activity_report_ids = {r.activity_report_id for r in records if r.activity_report_id}
    activities_map: dict[UUID, ActivityReport] = {}
    if activity_report_ids:
        acts = db.execute(
            select(ActivityReport).where(ActivityReport.id.in_(activity_report_ids))
        ).scalars().all()
        activities_map = {a.id: a for a in acts}

    return [
        _enrich(
            r,
            members_map.get(r.member_id),
            activities_map.get(r.activity_report_id) if r.activity_report_id else None,
        )
        for r in records
    ]


@router.post("", response_model=PaymentRecordRead)
def create_payment_record(
    payload: PaymentRecordCreate,
    db: Session = Depends(get_db),
) -> PaymentRecordRead:
    ensure_relations(db, payload.member_id, payload.transaction_id)
    record = PaymentRecord(**payload.model_dump())
    db.add(record)
    commit_or_400(db, "Could not create payment record")
    db.refresh(record)
    member = db.get(Member, record.member_id)
    return _enrich(record, member)


@router.get("/{payment_id}", response_model=PaymentRecordRead)
def get_payment_record(
    payment_id: UUID,
    db: Session = Depends(get_db),
) -> PaymentRecordRead:
    record = get_or_404(db, PaymentRecord, payment_id, "Payment record")
    member = db.get(Member, record.member_id)
    activity = db.get(ActivityReport, record.activity_report_id) if record.activity_report_id else None
    return _enrich(record, member, activity)


@router.patch("/{payment_id}", response_model=PaymentRecordRead)
def update_payment_record(
    payment_id: UUID,
    payload: PaymentRecordUpdate,
    db: Session = Depends(get_db),
) -> PaymentRecordRead:
    record = get_or_404(db, PaymentRecord, payment_id, "Payment record")
    data = payload.model_dump(exclude_unset=True)
    ensure_relations(db, data.get("member_id"), data.get("transaction_id"))
    apply_updates(record, payload)
    commit_or_400(db, "Could not update payment record")
    db.refresh(record)
    member = db.get(Member, record.member_id)
    activity = db.get(ActivityReport, record.activity_report_id) if record.activity_report_id else None
    return _enrich(record, member, activity)


@router.delete("/{payment_id}", response_model=PaymentRecordRead)
def delete_payment_record(
    payment_id: UUID,
    db: Session = Depends(get_db),
) -> PaymentRecordRead:
    record = get_or_404(db, PaymentRecord, payment_id, "Payment record")
    member = db.get(Member, record.member_id)
    activity = db.get(ActivityReport, record.activity_report_id) if record.activity_report_id else None
    enriched = _enrich(record, member, activity)
    db.delete(record)
    commit_or_400(db, "Could not delete payment record")
    return enriched


@router.post("/{payment_id}/unmatch")
def unmatch_payment_record(
    payment_id: UUID,
    db: Session = Depends(get_db),
) -> dict:
    """Cancel the transaction match for a payment record and restore unpaid status."""
    record: PaymentRecord = get_or_404(db, PaymentRecord, payment_id, "Payment record")

    # Revert linked transaction
    if record.transaction_id:
        txn = db.get(BankTransaction, record.transaction_id)
        if txn:
            txn.match_status = "unmatched"
            txn.matched_member_id = None
            # Keep payment_type for classification reference — only reset match_status

    # Reset payment record
    record.transaction_id = None
    record.paid_amount = 0
    record.status = _auto_status(0, int(record.required_amount or 0), None)
    record.payment_source = None

    commit_or_400(db, "Could not unmatch payment record")
    db.refresh(record)
    member = db.get(Member, record.member_id)
    return {
        "ok": True,
        "payment_record_id": str(record.id),
        "status": record.status,
        "paid_amount": record.paid_amount,
        "transaction_id": None,
    }


# ── Task 21: Refund status endpoints ──────────────────────────────────────────

class RefundPayload(BaseModel):
    refund_amount: int | None = None
    reason: str | None = None


class MarkRefundedPayload(BaseModel):
    refund_transaction_id: str | None = None
    refund_amount: int | None = None
    reason: str | None = None


class RefundCancelPayload(BaseModel):
    reason: str | None = None


@router.post("/{payment_id}/refund-required")
def set_refund_required(
    payment_id: UUID,
    payload: RefundPayload,
    db: Session = Depends(get_db),
) -> dict:
    from app.services.settlement_service import mark_refund_required
    try:
        record = mark_refund_required(db, payment_id, payload.refund_amount, payload.reason)
        db.commit()
        db.refresh(record)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {
        "ok": True,
        "payment_record_id": str(record.id),
        "refund_status": record.refund_status,
        "refund_amount": record.refund_amount,
    }


@router.post("/{payment_id}/refund-pending")
def set_refund_pending(
    payment_id: UUID,
    payload: RefundPayload,
    db: Session = Depends(get_db),
) -> dict:
    from app.services.settlement_service import mark_refund_pending
    try:
        record = mark_refund_pending(db, payment_id, payload.refund_amount, payload.reason)
        db.commit()
        db.refresh(record)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {
        "ok": True,
        "payment_record_id": str(record.id),
        "refund_status": record.refund_status,
        "refund_amount": record.refund_amount,
    }


@router.post("/{payment_id}/mark-refunded")
def set_mark_refunded(
    payment_id: UUID,
    payload: MarkRefundedPayload,
    db: Session = Depends(get_db),
) -> dict:
    from uuid import UUID as _UUID
    from app.services.settlement_service import mark_refunded
    txn_id = _UUID(payload.refund_transaction_id) if payload.refund_transaction_id else None
    try:
        record = mark_refunded(db, payment_id, txn_id, payload.refund_amount, payload.reason)
        db.commit()
        db.refresh(record)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {
        "ok": True,
        "payment_record_id": str(record.id),
        "refund_status": record.refund_status,
        "refund_amount": record.refund_amount,
        "status": record.status,
    }


@router.post("/{payment_id}/refund-cancel")
def refund_cancel(
    payment_id: UUID,
    payload: RefundCancelPayload,
    db: Session = Depends(get_db),
) -> dict:
    from app.services.settlement_service import cancel_refund
    try:
        record = cancel_refund(db, payment_id, payload.reason)
        db.commit()
        db.refresh(record)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {
        "ok": True,
        "payment_record_id": str(record.id),
        "refund_status": record.refund_status,
        "status": record.status,
    }


@router.get("/{payment_id}/adjustment-logs")
def get_adjustment_logs(
    payment_id: UUID,
    db: Session = Depends(get_db),
) -> list[dict]:
    from sqlalchemy import select as _select
    from app.models.payment import PaymentAdjustmentLog
    logs = list(db.scalars(
        _select(PaymentAdjustmentLog)
        .where(PaymentAdjustmentLog.payment_record_id == payment_id)
        .order_by(PaymentAdjustmentLog.created_at.desc())
    ))
    return [
        {
            "id": str(log.id),
            "action": log.action,
            "previous_status": log.previous_status,
            "new_status": log.new_status,
            "previous_paid_amount": log.previous_paid_amount,
            "new_paid_amount": log.new_paid_amount,
            "refund_amount": log.refund_amount,
            "reason": log.reason,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]


class ManualPaymentUpdatePayload(BaseModel):
    activity_id: UUID
    member_name: str | None = None
    student_id: str | None = None
    paid_amount: int | None = None
    payment_type: str = "activity_fee"
    raw_request: str | None = None


@router.post("/manual-update")
def manual_payment_update(
    payload: ManualPaymentUpdatePayload,
    db: Session = Depends(get_db),
) -> dict:
    """Apply a manual payment status change for a specific member in an activity."""
    from app.services.payment_manual_update_service import apply_manual_payment_update
    result = apply_manual_payment_update(
        db=db,
        activity_id=payload.activity_id,
        message=payload.raw_request or "",
        member_name=payload.member_name,
        student_id=payload.student_id,
        amount=payload.paid_amount,
        payment_type=payload.payment_type,
    )
    return {
        "ok": result.ok,
        "requires_confirmation": result.requires_confirmation,
        "member_name": result.member_name,
        "payment_type": result.payment_type,
        "activity_id": result.activity_id,
        "activity_title": result.activity_title,
        "required_amount": result.required_amount,
        "previous_paid_amount": result.previous_paid_amount,
        "new_paid_amount": result.new_paid_amount,
        "previous_status": result.previous_status,
        "new_status": result.new_status,
        "payment_record_id": result.payment_record_id,
        "message": result.message,
        "candidates": result.candidates,
    }


@router.put("/manual", response_model=PaymentRecordRead)
def upsert_manual_payment_record(
    payload: ManualPaymentPayload,
    db: Session = Depends(get_db),
) -> PaymentRecordRead:
    """Create or update a payment record directly without transaction matching."""
    member = db.get(Member, payload.member_id)
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found")

    status = _auto_status(payload.paid_amount, payload.required_amount, payload.status)
    # Auto-correct paid_amount for consistency
    paid_amount = _auto_paid_amount(status, payload.paid_amount, payload.required_amount)
    if payload.payment_type != "membership_fee":
        raise HTTPException(status_code=400, detail="This endpoint only supports membership_fee")

    existing: PaymentRecord | None = db.execute(
        select(PaymentRecord).where(
            and_(
                PaymentRecord.member_id == payload.member_id,
                PaymentRecord.period == payload.period,
                PaymentRecord.payment_type == payload.payment_type,
            )
        )
    ).scalar_one_or_none()

    if existing is not None:
        existing.required_amount = payload.required_amount
        existing.paid_amount = paid_amount
        existing.status = status
        existing.payment_source = "manual"
        existing.manual_note = payload.manual_note
        commit_or_400(db, "Could not update payment record")
        db.refresh(existing)
        activity = db.get(ActivityReport, existing.activity_report_id) if existing.activity_report_id else None
        return _enrich(existing, member, activity)
    else:
        record = PaymentRecord(
            member_id=payload.member_id,
            period=payload.period,
            payment_type=payload.payment_type,
            required_amount=payload.required_amount,
            paid_amount=paid_amount,
            status=status,
            payment_source="manual",
            manual_note=payload.manual_note,
        )
        db.add(record)
        commit_or_400(db, "Could not create payment record")
        db.refresh(record)
        return _enrich(record, member)


# ─── Membership fee bulk update (Task 37) ─────────────────────────────────────

class MembershipBulkUpdatePreviewPayload(BaseModel):
    period: str
    payment_record_ids: list[str]
    operation: str  # mark_paid | mark_unpaid | mark_need_check | mark_exempt | set_paid_amount
    paid_amount_value: int | None = None


class MembershipBulkUpdateConfirmPayload(BaseModel):
    action_id: str


@router.post("/membership/bulk-preview")
def membership_bulk_update_preview(
    payload: MembershipBulkUpdatePreviewPayload,
    db: Session = Depends(get_db),
) -> dict:
    """Preview bulk update for membership_fee records. Never modifies DB."""
    from app.services.membership_fee_bulk_update_service import preview_bulk_update

    try:
        result = preview_bulk_update(
            db=db,
            period=payload.period,
            payment_record_ids=payload.payment_record_ids,
            operation=payload.operation,
            paid_amount_value=payload.paid_amount_value,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"미리보기 생성 오류: {e}")

    return {
        "ok": result.ok,
        "requires_confirmation": result.requires_confirmation,
        "auto_apply": result.auto_apply,
        "action_id": result.action_id,
        "operation": result.operation,
        "period": result.period,
        "summary": {
            "selected": result.summary.selected,
            "will_change": result.summary.will_change,
            "no_change": result.summary.no_change,
            "will_be_paid": result.summary.will_be_paid,
            "will_be_exempt": result.summary.will_be_exempt,
            "will_be_unpaid": result.summary.will_be_unpaid,
            "will_be_need_check": result.summary.will_be_need_check,
            "danger": result.summary.danger,
            "danger_reason": result.summary.danger_reason,
        },
        "rows": [
            {
                "payment_record_id": row.payment_record_id,
                "member_id": row.member_id,
                "member_name": row.member_name,
                "student_id": row.student_id,
                "before_required_amount": row.before_required_amount,
                "before_paid_amount": row.before_paid_amount,
                "before_status": row.before_status,
                "after_required_amount": row.after_required_amount,
                "after_paid_amount": row.after_paid_amount,
                "after_status": row.after_status,
                "will_change": row.will_change,
                "note": row.note,
            }
            for row in result.rows
        ],
    }


@router.post("/membership/bulk-confirm")
def membership_bulk_update_confirm(
    payload: MembershipBulkUpdateConfirmPayload,
    db: Session = Depends(get_db),
) -> dict:
    """Apply a previewed bulk update proposal. Re-validates scope before applying."""
    from app.services.membership_fee_bulk_update_service import confirm_bulk_update

    try:
        action_id = UUID(payload.action_id)
        result = confirm_bulk_update(db=db, action_id=action_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"반영 오류: {e}")

    return {
        "ok": result.ok,
        "operation": result.operation,
        "period": result.period,
        "updated_count": result.updated_count,
        "skipped_count": result.skipped_count,
        "rows_updated": result.rows_updated,
    }
