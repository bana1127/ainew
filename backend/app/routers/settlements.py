"""Settlement summary and refund list API.

GET /api/settlements/summary   — aggregated settlement stats
GET /api/settlements/refunds   — list of records needing/pending/completed refunds
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Member
from app.models.activity import ActivityReport
from app.models.payment import PaymentRecord


router = APIRouter()


@router.get("/summary")
def settlement_summary(
    activity_id: UUID | None = None,
    period: str | None = None,
    payment_type: str = "activity_fee",
    db: Session = Depends(get_db),
) -> dict:
    stmt = select(PaymentRecord).where(PaymentRecord.payment_type == payment_type)
    if activity_id:
        stmt = stmt.where(PaymentRecord.activity_report_id == activity_id)
    if period:
        stmt = stmt.where(PaymentRecord.period == period)

    records = list(db.scalars(stmt))
    total_required = sum(r.required_amount or 0 for r in records)
    total_paid = sum(r.paid_amount or 0 for r in records)
    overpaid_list = [r for r in records if r.status == "overpaid"]
    total_overpaid = sum(max(0, (r.paid_amount or 0) - (r.required_amount or 0)) for r in overpaid_list)
    refund_req_list = [r for r in records if r.refund_status == "refund_required"]
    total_refund_required = sum(r.refund_amount or 0 for r in refund_req_list)

    return {
        "total_records": len(records),
        "paid_count": sum(1 for r in records if r.status == "paid"),
        "unpaid_count": sum(1 for r in records if r.status == "unpaid"),
        "partial_count": sum(1 for r in records if r.status == "partial"),
        "overpaid_count": len(overpaid_list),
        "refund_required_count": len(refund_req_list),
        "refunded_count": sum(1 for r in records if r.refund_status == "refunded"),
        "need_check_count": sum(1 for r in records if r.status == "need_check"),
        "cancelled_count": sum(1 for r in records if r.status == "cancelled"),
        "total_required_amount": total_required,
        "total_paid_amount": total_paid,
        "total_overpaid_amount": total_overpaid,
        "total_refund_required_amount": total_refund_required,
    }


@router.get("/refunds")
def list_refund_records(
    activity_id: UUID | None = None,
    refund_status: str | None = None,
    db: Session = Depends(get_db),
) -> list[dict]:
    stmt = select(PaymentRecord).where(
        PaymentRecord.payment_type == "activity_fee",
    )
    if activity_id:
        stmt = stmt.where(PaymentRecord.activity_report_id == activity_id)
    if refund_status:
        stmt = stmt.where(PaymentRecord.refund_status == refund_status)
    else:
        stmt = stmt.where(
            PaymentRecord.refund_status.in_(["refund_required", "refund_pending", "refunded"])
        )

    records = list(db.scalars(stmt))
    result = []
    for r in records:
        member = db.get(Member, r.member_id) if r.member_id else None
        activity = db.get(ActivityReport, r.activity_report_id) if r.activity_report_id else None

        # Participant status
        participant_status = None
        if r.activity_report_id:
            from sqlalchemy import and_
            from app.models.activity import ActivityParticipant
            p = db.scalar(
                select(ActivityParticipant).where(
                    and_(
                        ActivityParticipant.activity_report_id == r.activity_report_id,
                        ActivityParticipant.member_id == r.member_id,
                    )
                )
            )
            if p:
                participant_status = p.status

        overpaid = max(0, (r.paid_amount or 0) - (r.required_amount or 0))
        result.append({
            "payment_record_id": str(r.id),
            "member_id": str(r.member_id) if r.member_id else None,
            "member_name": member.name if member else None,
            "student_id": member.student_id if member else None,
            "activity_id": str(r.activity_report_id) if r.activity_report_id else None,
            "activity_title": activity.title if activity else None,
            "participant_status": participant_status,
            "required_amount": r.required_amount,
            "paid_amount": r.paid_amount,
            "overpaid_amount": overpaid,
            "refund_amount": r.refund_amount,
            "refund_status": r.refund_status or "none",
            "refund_reason": r.refund_reason,
            "status": r.status,
            "refunded_at": r.refunded_at.isoformat() if r.refunded_at else None,
        })
    return result
