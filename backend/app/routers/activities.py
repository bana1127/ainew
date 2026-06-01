"""Activity-centric router.

ActivityReport is used as the Activity entity.
This router provides /api/activities endpoints that expose activity data
with aggregated summary fields needed by the frontend.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.models import ActivityCategory, ActivityParticipant, ActivityReport, Member
from app.models.payment import PaymentRecord
from app.models.receipt import Receipt
from app.routers.common import apply_updates, commit_or_400, get_or_404

router = APIRouter()


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _activity_summary(report: ActivityReport, db: Session) -> dict:
    """Build the summary dict for an activity card."""
    participant_count = db.scalar(
        select(func.count(ActivityParticipant.id)).where(
            ActivityParticipant.activity_report_id == report.id
        )
    ) or 0

    receipt_rows = list(db.scalars(
        select(Receipt).where(Receipt.activity_report_id == report.id)
    ))
    receipt_count = len(receipt_rows)
    need_check_count = sum(1 for r in receipt_rows if r.need_check)

    period_key = f"act-{str(report.id)[:8]}"
    fee_records = list(db.scalars(
        select(PaymentRecord).where(
            and_(
                PaymentRecord.period == period_key,
                PaymentRecord.payment_type == "activity_fee",
            )
        )
    ))
    if fee_records:
        paid_count = sum(1 for r in fee_records if r.status == "paid")
        activity_fee_status = f"{paid_count}/{len(fee_records)} 납부"
    else:
        activity_fee_status = "미설정"

    category_name: str | None = None
    if report.category_id:
        cat = db.get(ActivityCategory, report.category_id)
        category_name = cat.name if cat else None

    return {
        "id": str(report.id),
        "title": report.title,
        "activity_date": str(report.activity_date) if report.activity_date else None,
        "location": report.location,
        "category_name": category_name,
        "category_id": str(report.category_id) if report.category_id else None,
        "participant_count": participant_count,
        "report_status": report.status,
        "activity_fee_status": activity_fee_status,
        "receipt_count": receipt_count,
        "need_check_count": need_check_count,
        "status": report.status,
        "created_at": report.created_at.isoformat() if report.created_at else None,
        "updated_at": report.updated_at.isoformat() if report.updated_at else None,
    }


# ─── List ──────────────────────────────────────────────────────────────────────

@router.get("")
def list_activities(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    category_id: UUID | None = None,
    status: str | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
) -> list[dict]:
    stmt = select(ActivityReport)
    if category_id:
        stmt = stmt.where(ActivityReport.category_id == category_id)
    if status:
        stmt = stmt.where(ActivityReport.status == status)
    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(
            or_(
                ActivityReport.title.ilike(pattern),
                ActivityReport.location.ilike(pattern),
            )
        )
    reports = list(db.scalars(stmt.order_by(ActivityReport.activity_date.desc().nullslast()).offset(skip).limit(limit)))
    return [_activity_summary(r, db) for r in reports]


# ─── Create ────────────────────────────────────────────────────────────────────

class ActivityCreatePayload(BaseModel):
    title: str
    category_id: UUID | None = None
    activity_date: str | None = None
    location: str | None = None
    description: str | None = None
    participant_member_ids: list[UUID] = []
    status: str = "planned"


@router.post("")
def create_activity(
    payload: ActivityCreatePayload,
    db: Session = Depends(get_db),
) -> dict:
    if payload.category_id and db.get(ActivityCategory, payload.category_id) is None:
        raise HTTPException(status_code=404, detail="Activity category not found")

    report = ActivityReport(
        title=payload.title,
        category_id=payload.category_id,
        activity_date=payload.activity_date,
        location=payload.location,
        input_text=payload.description,
        status=payload.status,
    )
    db.add(report)
    db.flush()

    for mid in payload.participant_member_ids:
        if db.get(Member, mid) is None:
            raise HTTPException(status_code=404, detail=f"Member {mid} not found")
        db.add(ActivityParticipant(activity_report_id=report.id, member_id=mid, role="participant"))

    commit_or_400(db, "Could not create activity")
    db.refresh(report)
    return _activity_summary(report, db)


# ─── Detail ────────────────────────────────────────────────────────────────────

@router.get("/{activity_id}")
def get_activity_detail(activity_id: UUID, db: Session = Depends(get_db)) -> dict:
    """Full activity detail with participants, receipts, and fee records."""
    report: ActivityReport = get_or_404(db, ActivityReport, activity_id, "Activity")

    participants = list(db.scalars(
        select(ActivityParticipant)
        .where(ActivityParticipant.activity_report_id == activity_id)
        .options(selectinload(ActivityParticipant.member))
    ))

    category_name: str | None = None
    if report.category_id:
        cat = db.get(ActivityCategory, report.category_id)
        category_name = cat.name if cat else None

    receipts = list(db.scalars(
        select(Receipt).where(Receipt.activity_report_id == activity_id)
    ))

    period_key = f"act-{str(activity_id)[:8]}"
    fee_records = list(db.scalars(
        select(PaymentRecord).where(
            and_(
                PaymentRecord.period == period_key,
                PaymentRecord.payment_type == "activity_fee",
            )
        )
    ))

    fee_member_ids = {r.member_id for r in fee_records}
    fee_members: dict[UUID, Member] = {}
    if fee_member_ids:
        for m in db.scalars(select(Member).where(Member.id.in_(fee_member_ids))):
            fee_members[m.id] = m

    fee_list = [
        {
            "id": str(r.id),
            "member_id": str(r.member_id),
            "member_name": fee_members[r.member_id].name if r.member_id in fee_members else None,
            "student_id": fee_members[r.member_id].student_id if r.member_id in fee_members else None,
            "required_amount": r.required_amount,
            "paid_amount": r.paid_amount,
            "status": r.status,
            "period": r.period,
        }
        for r in fee_records
    ]

    fee_enabled = len(fee_records) > 0
    fee_amount = fee_records[0].required_amount if fee_records else 0
    paid_count = sum(1 for r in fee_records if r.status == "paid")

    has_participants = len(participants) > 0
    has_report = bool(report.final_content or report.generated_content)
    has_fee = fee_enabled
    fee_paid = paid_count == len(fee_records) and len(fee_records) > 0
    has_receipts = len(receipts) > 0
    receipts_ok = all(r.evidence_status == "valid" for r in receipts) if receipts else True

    checklist = [
        {"key": "participants", "label": "참여자 등록", "done": has_participants, "count": len(participants)},
        {"key": "report", "label": "보고서 작성", "done": has_report},
        {"key": "activity_fee_setup", "label": "활동비 설정", "done": has_fee},
        {"key": "activity_fee_paid", "label": "활동비 납부 완료", "done": fee_paid,
         "detail": f"{paid_count}/{len(fee_records)}" if fee_records else None},
        {"key": "receipts", "label": "영수증 연결", "done": has_receipts, "count": len(receipts)},
        {"key": "receipts_ok", "label": "증빙 확인", "done": receipts_ok},
    ]

    return {
        "activity": {
            "id": str(report.id),
            "title": report.title,
            "activity_date": str(report.activity_date) if report.activity_date else None,
            "location": report.location,
            "category_id": str(report.category_id) if report.category_id else None,
            "category_name": category_name,
            "input_text": report.input_text,
            "generated_content": report.generated_content,
            "final_content": report.final_content,
            "status": report.status,
            "created_at": report.created_at.isoformat() if report.created_at else None,
            "updated_at": report.updated_at.isoformat() if report.updated_at else None,
        },
        "participants": [
            {
                "id": str(p.id),
                "member_id": str(p.member_id),
                "name": p.member.name if p.member else None,
                "student_id": p.member.student_id if p.member else None,
                "department": p.member.department if p.member else None,
                "role": p.role,
            }
            for p in participants
        ],
        "receipts": [
            {
                "id": str(r.id),
                "receipt_date": str(r.receipt_date) if r.receipt_date else None,
                "store_name": r.store_name,
                "amount": r.amount,
                "payment_method": r.payment_method,
                "category": r.category,
                "evidence_status": r.evidence_status,
                "need_check": r.need_check,
                "reason": r.reason,
            }
            for r in receipts
        ],
        "activity_fee": {
            "enabled": fee_enabled,
            "amount": fee_amount,
            "period_key": period_key,
            "paid_count": paid_count,
            "total_count": len(fee_records),
            "records": fee_list,
        },
        "checklist": checklist,
    }


# ─── Update ────────────────────────────────────────────────────────────────────

class ActivityUpdatePayload(BaseModel):
    title: str | None = None
    category_id: UUID | None = None
    activity_date: str | None = None
    location: str | None = None
    description: str | None = None
    status: str | None = None


@router.patch("/{activity_id}")
def update_activity(
    activity_id: UUID,
    payload: ActivityUpdatePayload,
    db: Session = Depends(get_db),
) -> dict:
    report: ActivityReport = get_or_404(db, ActivityReport, activity_id, "Activity")
    data = payload.model_dump(exclude_unset=True)
    if "description" in data:
        report.input_text = data.pop("description")
    for key, val in data.items():
        setattr(report, key, val)
    commit_or_400(db, "Could not update activity")
    db.refresh(report)
    return _activity_summary(report, db)


# ─── Archive / Delete ──────────────────────────────────────────────────────────

@router.delete("/{activity_id}")
def archive_activity(
    activity_id: UUID,
    db: Session = Depends(get_db),
) -> dict:
    report: ActivityReport = get_or_404(db, ActivityReport, activity_id, "Activity")
    report.status = "archived"
    commit_or_400(db, "Could not archive activity")
    db.refresh(report)
    return _activity_summary(report, db)


# ─── Participants ──────────────────────────────────────────────────────────────

class ParticipantAddPayload(BaseModel):
    member_id: UUID
    role: str = "participant"


@router.post("/{activity_id}/participants")
def add_participant(
    activity_id: UUID,
    payload: ParticipantAddPayload,
    db: Session = Depends(get_db),
) -> dict:
    get_or_404(db, ActivityReport, activity_id, "Activity")
    if db.get(Member, payload.member_id) is None:
        raise HTTPException(status_code=404, detail="Member not found")

    existing = db.scalar(
        select(ActivityParticipant).where(
            and_(
                ActivityParticipant.activity_report_id == activity_id,
                ActivityParticipant.member_id == payload.member_id,
            )
        )
    )
    if existing:
        raise HTTPException(status_code=400, detail="Already a participant")

    participant = ActivityParticipant(
        activity_report_id=activity_id,
        member_id=payload.member_id,
        role=payload.role,
    )
    db.add(participant)
    commit_or_400(db, "Could not add participant")
    db.refresh(participant)

    member = db.get(Member, payload.member_id)
    return {
        "id": str(participant.id),
        "member_id": str(participant.member_id),
        "name": member.name if member else None,
        "student_id": member.student_id if member else None,
        "department": member.department if member else None,
        "role": participant.role,
    }


@router.delete("/{activity_id}/participants/{member_id}")
def remove_participant(
    activity_id: UUID,
    member_id: UUID,
    db: Session = Depends(get_db),
) -> dict:
    get_or_404(db, ActivityReport, activity_id, "Activity")
    participant = db.scalar(
        select(ActivityParticipant).where(
            and_(
                ActivityParticipant.activity_report_id == activity_id,
                ActivityParticipant.member_id == member_id,
            )
        )
    )
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")
    db.delete(participant)
    commit_or_400(db, "Could not remove participant")
    return {"ok": True}


# ─── Activity Fees ─────────────────────────────────────────────────────────────

class ActivityFeeGeneratePayload(BaseModel):
    fee_amount: int = 10000
    period: str | None = None


@router.post("/{activity_id}/activity-fees/generate")
def generate_activity_fees(
    activity_id: UUID,
    payload: ActivityFeeGeneratePayload,
    db: Session = Depends(get_db),
) -> dict:
    report: ActivityReport = get_or_404(db, ActivityReport, activity_id, "Activity")

    participants = list(db.scalars(
        select(ActivityParticipant).where(ActivityParticipant.activity_report_id == activity_id)
    ))
    if not participants:
        raise HTTPException(status_code=400, detail="참여자가 없습니다. 먼저 참여자를 추가하세요.")

    period_key = payload.period or f"act-{str(activity_id)[:8]}"

    created = 0
    skipped = 0
    for p in participants:
        existing = db.execute(
            select(PaymentRecord).where(
                and_(
                    PaymentRecord.member_id == p.member_id,
                    PaymentRecord.period == period_key,
                    PaymentRecord.payment_type == "activity_fee",
                )
            )
        ).scalar_one_or_none()

        if existing:
            if existing.status not in ("paid", "partial", "exempt"):
                existing.required_amount = payload.fee_amount
            skipped += 1
        else:
            record = PaymentRecord(
                member_id=p.member_id,
                period=period_key,
                payment_type="activity_fee",
                required_amount=payload.fee_amount,
                paid_amount=0,
                status="unpaid",
                activity_report_id=activity_id,
            )
            db.add(record)
            created += 1

    db.commit()
    return {
        "ok": True,
        "period_key": period_key,
        "fee_amount": payload.fee_amount,
        "created": created,
        "skipped": skipped,
        "total": len(participants),
    }


@router.patch("/{activity_id}/activity-fees/{record_id}")
def update_activity_fee_record(
    activity_id: UUID,
    record_id: UUID,
    payload: dict,
    db: Session = Depends(get_db),
) -> dict:
    get_or_404(db, ActivityReport, activity_id, "Activity")
    record = db.get(PaymentRecord, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Payment record not found")

    allowed = {"paid_amount", "status", "required_amount"}
    for key, val in payload.items():
        if key in allowed:
            setattr(record, key, val)

    if "paid_amount" in payload and "status" not in payload:
        if record.paid_amount >= record.required_amount:
            record.status = "paid"
        elif record.paid_amount > 0:
            record.status = "partial"
        else:
            record.status = "unpaid"

    commit_or_400(db, "Could not update payment record")
    db.refresh(record)
    return {
        "id": str(record.id),
        "member_id": str(record.member_id),
        "required_amount": record.required_amount,
        "paid_amount": record.paid_amount,
        "status": record.status,
    }
