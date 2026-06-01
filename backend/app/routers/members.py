from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import ActivityParticipant, ActivityReport, Member
from app.models.payment import PaymentRecord
from app.routers.common import apply_updates, commit_or_400, get_or_404
from app.schemas import MemberCreate, MemberRead, MemberUpdate


router = APIRouter()


@router.get("", response_model=list[MemberRead])
def list_members(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    status: str | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
) -> list[Member]:
    statement = select(Member)
    if status:
        statement = statement.where(Member.status == status)
    if q:
        pattern = f"%{q}%"
        statement = statement.where(
            or_(
                Member.name.ilike(pattern),
                Member.student_id.ilike(pattern),
                Member.department.ilike(pattern),
            )
        )
    return list(db.scalars(statement.offset(skip).limit(limit)))


@router.post("", response_model=MemberRead)
def create_member(payload: MemberCreate, db: Session = Depends(get_db)) -> Member:
    if payload.student_id and db.scalar(
        select(Member).where(Member.student_id == payload.student_id)
    ):
        raise HTTPException(status_code=400, detail="student_id already exists")
    member = Member(**payload.model_dump())
    db.add(member)
    commit_or_400(db, "Could not create member")
    db.refresh(member)
    return member


@router.get("/{member_id}", response_model=MemberRead)
def get_member(member_id: UUID, db: Session = Depends(get_db)) -> Member:
    return get_or_404(db, Member, member_id, "Member")


@router.patch("/{member_id}", response_model=MemberRead)
def update_member(
    member_id: UUID,
    payload: MemberUpdate,
    db: Session = Depends(get_db),
) -> Member:
    member = get_or_404(db, Member, member_id, "Member")
    data = payload.model_dump(exclude_unset=True)
    if "student_id" in data and data["student_id"]:
        duplicate = db.scalar(
            select(Member).where(
                Member.student_id == data["student_id"],
                Member.id != member_id,
            )
        )
        if duplicate:
            raise HTTPException(status_code=400, detail="student_id already exists")
    apply_updates(member, payload)
    commit_or_400(db, "Could not update member")
    db.refresh(member)
    return member


@router.delete("/{member_id}", response_model=MemberRead)
def delete_member(member_id: UUID, db: Session = Depends(get_db)) -> Member:
    member = get_or_404(db, Member, member_id, "Member")
    member.status = "inactive"
    commit_or_400(db, "Could not deactivate member")
    db.refresh(member)
    return member


@router.get("/{member_id}/summary")
def get_member_summary(member_id: UUID, db: Session = Depends(get_db)) -> dict:
    """Return member profile + activity/payment history."""
    member: Member = get_or_404(db, Member, member_id, "Member")

    # Participated activities (via ActivityParticipant)
    participants = list(db.scalars(
        select(ActivityParticipant)
        .where(ActivityParticipant.member_id == member_id)
    ))
    activity_report_ids = [p.activity_report_id for p in participants]
    activities = []
    if activity_report_ids:
        reports = list(db.scalars(
            select(ActivityReport).where(ActivityReport.id.in_(activity_report_ids))
        ))
        for r in reports:
            p_row = next((p for p in participants if p.activity_report_id == r.id), None)
            activities.append({
                "id": str(r.id),
                "title": r.title,
                "activity_date": str(r.activity_date) if r.activity_date else None,
                "location": r.location,
                "status": r.status,
                "role": p_row.role if p_row else None,
            })

    # All payment records for this member
    payment_records = list(db.scalars(
        select(PaymentRecord).where(PaymentRecord.member_id == member_id)
    ))
    membership_payments = [
        {"id": str(r.id), "period": r.period, "required_amount": r.required_amount,
         "paid_amount": r.paid_amount, "status": r.status}
        for r in payment_records if r.payment_type == "membership_fee"
    ]
    activity_fee_payments = [
        {"id": str(r.id), "period": r.period, "payment_type": r.payment_type,
         "required_amount": r.required_amount, "paid_amount": r.paid_amount, "status": r.status}
        for r in payment_records if r.payment_type == "activity_fee"
    ]

    unpaid_membership = sum(1 for r in payment_records if r.payment_type == "membership_fee" and r.status == "unpaid")
    unpaid_activity = sum(1 for r in payment_records if r.payment_type == "activity_fee" and r.status == "unpaid")

    return {
        "member": {
            "id": str(member.id),
            "name": member.name,
            "student_id": member.student_id,
            "department": member.department,
            "phone": member.phone,
            "email": member.email,
            "status": member.status,
            "memo": member.memo,
        },
        "activities": activities,
        "membership_payments": membership_payments,
        "activity_fee_payments": activity_fee_payments,
        "summary": {
            "activity_count": len(activities),
            "membership_paid_count": sum(1 for r in payment_records if r.payment_type == "membership_fee" and r.status == "paid"),
            "unpaid_membership_count": unpaid_membership,
            "unpaid_activity_fee_count": unpaid_activity,
        },
    }

