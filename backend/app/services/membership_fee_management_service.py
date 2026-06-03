from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.services.membership_fee_policy import (
    DEFAULT_EXISTING_MEMBER_FEE,
    DEFAULT_EXECUTIVE_FEE,
    DEFAULT_NEW_MEMBER_FEE,
    PAYMENT_TYPE,
    apply_membership_fee_generation,
    payment_status,
    preview_membership_fee_generation,
)

UNPAID_STATUSES = {"unpaid", "partial", "need_check"}
SETTLED_STATUSES = {"paid", "exempt", "cancelled"}


@dataclass(frozen=True)
class MembershipFeeSummary:
    period: str
    payment_type: str
    required_amount: int
    total_members: int
    paid_count: int
    partial_count: int
    unpaid_count: int
    need_check_count: int
    exempt_count: int
    overpaid_count: int
    missing_record_count: int
    total_required_amount: int
    total_paid_amount: int
    receivable_amount: int


def calculate_status(required_amount: int, paid_amount: int) -> str:
    return payment_status(int(paid_amount or 0), int(required_amount or 0))


def get_membership_fee_summary(
    db: Session,
    *,
    period: str | None,
    new_member_fee: int = DEFAULT_NEW_MEMBER_FEE,
    existing_member_fee: int = DEFAULT_EXISTING_MEMBER_FEE,
    executive_fee: int = DEFAULT_EXECUTIVE_FEE,
) -> MembershipFeeSummary:
    preview = preview_membership_fee_generation(
        db=db,
        period=period,
        new_member_fee=new_member_fee,
        existing_member_fee=existing_member_fee,
        executive_fee=executive_fee,
    )
    rows = preview.rows
    return MembershipFeeSummary(
        period=preview.current_term,
        payment_type=PAYMENT_TYPE,
        required_amount=preview.new_member_fee,
        total_members=len(rows),
        paid_count=sum(1 for row in rows if row.status == "paid"),
        partial_count=sum(1 for row in rows if row.status == "partial"),
        unpaid_count=sum(1 for row in rows if row.status == "unpaid"),
        need_check_count=sum(1 for row in rows if row.status == "need_check"),
        exempt_count=sum(1 for row in rows if row.status == "exempt"),
        overpaid_count=sum(1 for row in rows if row.status == "overpaid"),
        missing_record_count=sum(1 for row in rows if row.existing_record_id is None),
        total_required_amount=sum(row.required_amount for row in rows),
        total_paid_amount=sum(row.paid_amount for row in rows),
        receivable_amount=sum(
            max(0, row.required_amount - row.paid_amount)
            for row in rows
            if row.status in UNPAID_STATUSES
        ),
    )


def preview_sync_targets(
    db: Session,
    *,
    period: str | None,
    new_member_fee: int = DEFAULT_NEW_MEMBER_FEE,
    existing_member_fee: int = DEFAULT_EXISTING_MEMBER_FEE,
    executive_fee: int = DEFAULT_EXECUTIVE_FEE,
) -> dict[str, Any]:
    from app.services.assistant_action_service import create_action_proposal

    preview = preview_membership_fee_generation(
        db=db,
        period=period,
        new_member_fee=new_member_fee,
        existing_member_fee=existing_member_fee,
        executive_fee=executive_fee,
    )
    proposal = create_action_proposal(
        db,
        action_type="membership_fee_generate",
        source="payments_membership_sync",
        activity_id=None,
        payload={
            "period": preview.current_term,
            "new_member_fee": new_member_fee,
            "existing_member_fee": existing_member_fee,
            "executive_fee": executive_fee,
        },
        preview={
            "period": preview.current_term,
            "payment_type": PAYMENT_TYPE,
            "created_count": preview.summary.created_count,
            "updated_count": preview.summary.updated_count,
            "total_required_amount": preview.summary.total_required_amount,
        },
        confidence=1.0,
        risk_level="medium",
    )
    preview.action_id = str(proposal.id)
    return {"preview": preview, "action_id": str(proposal.id)}


def confirm_sync_targets(db: Session, *, action_id: UUID) -> dict[str, Any]:
    from app.services.assistant_action_service import confirm_action_proposal

    proposal, result = confirm_action_proposal(db, action_id)
    if proposal.action_type != "membership_fee_generate":
        raise ValueError("Action proposal is not a membership fee sync proposal")
    return {
        "ok": True,
        "action_id": str(proposal.id),
        "status": proposal.status,
        "result": result,
    }


def apply_membership_record_manual_update(
    db: Session,
    *,
    payment_record_id: UUID,
    required_amount: int | None = None,
    paid_amount: int | None = None,
    status: str | None = None,
    manual_note: str | None = None,
) -> Any:
    from app.models import PaymentRecord
    from app.models.payment import PaymentAdjustmentLog

    record = db.get(PaymentRecord, payment_record_id)
    if record is None:
        raise ValueError("PaymentRecord not found")
    if record.payment_type != PAYMENT_TYPE:
        raise ValueError("Only membership_fee records can be manually updated here")

    before_required = int(record.required_amount or 0)
    before_paid = int(record.paid_amount or 0)
    before_status = record.status

    next_required = before_required if required_amount is None else max(0, int(required_amount))
    next_paid = before_paid if paid_amount is None else max(0, int(paid_amount))

    if status == "exempt":
        next_required = 0
        next_paid = 0
        next_status = "exempt"
    elif status == "need_check":
        next_status = "need_check"
    else:
        next_status = calculate_status(next_required, next_paid)

    record.required_amount = next_required
    record.paid_amount = next_paid
    record.status = next_status
    record.transaction_id = record.transaction_id
    record.payment_source = "transaction_match" if record.transaction_id else "manual"
    if manual_note is not None:
        record.manual_note = manual_note

    db.add(
        PaymentAdjustmentLog(
            payment_record_id=record.id,
            transaction_id=record.transaction_id,
            action="membership_fee_manual_update",
            previous_status=before_status,
            new_status=next_status,
            previous_paid_amount=before_paid,
            new_paid_amount=next_paid,
            reason=manual_note,
            metadata_json={
                "before_required_amount": before_required,
                "after_required_amount": next_required,
                "payment_source": record.payment_source,
            },
        )
    )
    db.commit()
    db.refresh(record)
    return record


def sync_membership_targets_now(
    db: Session,
    *,
    period: str | None,
    new_member_fee: int = DEFAULT_NEW_MEMBER_FEE,
    existing_member_fee: int = DEFAULT_EXISTING_MEMBER_FEE,
    executive_fee: int = DEFAULT_EXECUTIVE_FEE,
) -> dict[str, Any]:
    return apply_membership_fee_generation(
        db=db,
        period=period,
        new_member_fee=new_member_fee,
        existing_member_fee=existing_member_fee,
        executive_fee=executive_fee,
    )


def active_membership_record_ids(db: Session, *, period: str) -> set[UUID]:
    from app.models import Member, PaymentRecord

    active_member_ids = set(db.scalars(select(Member.id).where(Member.status == "active")))
    return set(
        db.scalars(
            select(PaymentRecord.id).where(
                and_(
                    PaymentRecord.period == period,
                    PaymentRecord.payment_type == PAYMENT_TYPE,
                    PaymentRecord.member_id.in_(active_member_ids),
                )
            )
        )
    )
