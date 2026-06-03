"""Bulk Membership Fee Mark Paid Service (Task 28).

각 부원의 PaymentRecord.required_amount를 기준으로
paid_amount = required_amount, status = paid (또는 exempt if required=0)
로 일괄 완납 처리합니다.

절대 단일 금액(30,000원 등)을 사용하지 않습니다.
activity_fee는 절대 수정하지 않습니다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.models.member import Member
from app.models.payment import PaymentRecord


@dataclass
class BulkMarkPaidPreviewItem:
    payment_record_id: str
    member_id: str
    member_name: str | None
    student_id: str | None
    required_amount: int
    previous_paid_amount: int
    previous_status: str
    new_paid_amount: int
    new_status: str
    member_type: str  # "new_member" | "existing_member" | "executive"


@dataclass
class BulkMarkPaidSummary:
    period: str
    total_records: int
    new_member_count: int
    existing_member_count: int
    executive_count: int
    will_change_count: int
    already_paid_count: int
    total_amount: int


@dataclass
class BulkMarkPaidPreviewResult:
    period: str
    summary: BulkMarkPaidSummary
    items: list[BulkMarkPaidPreviewItem]


@dataclass
class BulkMarkPaidApplyResult:
    ok: bool
    period: str
    updated_count: int
    skipped_count: int


def _infer_member_type(member: Member) -> str:
    """Infer member type for display purposes."""
    if member.is_executive or getattr(member, "is_officer", False):
        return "executive"
    # Heuristic: if joined_term or grade suggests new member
    grade = getattr(member, "grade", None) or ""
    if "1" in grade and "학년" in grade:
        return "new_member"
    return "existing_member"


def _new_status(required: int, paid: int) -> str:
    if required == 0:
        return "exempt"
    if paid >= required:
        return "paid"
    if paid > 0:
        return "partial"
    return "unpaid"


def preview_bulk_membership_fee_mark_paid(
    db: Session,
    period: str,
) -> BulkMarkPaidPreviewResult:
    """Generate preview for bulk mark paid.

    Uses each record's own required_amount — never a fixed amount.
    Only membership_fee records are included (never activity_fee).
    """
    records = list(
        db.scalars(
            select(PaymentRecord).where(
                and_(
                    PaymentRecord.period == period,
                    PaymentRecord.payment_type == "membership_fee",
                )
            )
        )
    )

    items: list[BulkMarkPaidPreviewItem] = []
    new_member_count = 0
    existing_member_count = 0
    executive_count = 0
    will_change_count = 0
    already_paid_count = 0
    total_amount = 0

    for rec in records:
        member = db.get(Member, rec.member_id) if rec.member_id else None
        member_name = member.name if member else None
        student_id = member.student_id if member else None

        required = rec.required_amount or 0
        member_type = _infer_member_type(member) if member else "existing_member"

        # Determine new status
        new_paid = required
        new_st = "paid" if required > 0 else "exempt"

        will_change = rec.status not in ("paid", "exempt") or rec.paid_amount != new_paid

        if member_type == "executive":
            executive_count += 1
        elif member_type == "new_member":
            new_member_count += 1
        else:
            existing_member_count += 1

        if will_change:
            will_change_count += 1
        else:
            already_paid_count += 1

        total_amount += required

        items.append(BulkMarkPaidPreviewItem(
            payment_record_id=str(rec.id),
            member_id=str(rec.member_id) if rec.member_id else "",
            member_name=member_name,
            student_id=student_id,
            required_amount=required,
            previous_paid_amount=rec.paid_amount or 0,
            previous_status=rec.status or "unpaid",
            new_paid_amount=new_paid,
            new_status=new_st,
            member_type=member_type,
        ))

    summary = BulkMarkPaidSummary(
        period=period,
        total_records=len(records),
        new_member_count=new_member_count,
        existing_member_count=existing_member_count,
        executive_count=executive_count,
        will_change_count=will_change_count,
        already_paid_count=already_paid_count,
        total_amount=total_amount,
    )

    return BulkMarkPaidPreviewResult(period=period, summary=summary, items=items)


def apply_bulk_membership_fee_mark_paid(
    db: Session,
    period: str,
) -> BulkMarkPaidApplyResult:
    """Apply bulk mark paid.

    Sets paid_amount = required_amount for each membership_fee record.
    Never touches activity_fee records.
    """
    records = list(
        db.scalars(
            select(PaymentRecord).where(
                and_(
                    PaymentRecord.period == period,
                    PaymentRecord.payment_type == "membership_fee",
                )
            )
        )
    )

    updated = 0
    skipped = 0

    for rec in records:
        required = rec.required_amount or 0
        new_paid = required
        new_st = "paid" if required > 0 else "exempt"

        if rec.status in ("paid", "exempt") and rec.paid_amount == new_paid:
            skipped += 1
            continue

        rec.paid_amount = new_paid
        rec.status = new_st
        updated += 1

    db.commit()

    return BulkMarkPaidApplyResult(
        ok=True,
        period=period,
        updated_count=updated,
        skipped_count=skipped,
    )
