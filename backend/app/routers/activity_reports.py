from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.models import ActivityCategory, ActivityParticipant, ActivityReport, Member
from app.models.payment import PaymentRecord
from app.models.receipt import Receipt
from app.routers.common import apply_updates, commit_or_400, get_or_404
from app.schemas import (
    ActivityParticipantWithMemberRead,
    ActivityReportCreate,
    ActivityReportRead,
    ActivityReportUpdate,
    ParticipantsBulkUpdate,
)


router = APIRouter()


def ensure_category(db: Session, category_id: UUID | None) -> None:
    if category_id and db.get(ActivityCategory, category_id) is None:
        raise HTTPException(status_code=404, detail="Activity category not found")


@router.get("", response_model=list[ActivityReportRead])
def list_activity_reports(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    category_id: UUID | None = None,
    status: str | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
) -> list[ActivityReport]:
    statement = select(ActivityReport)
    if category_id:
        statement = statement.where(ActivityReport.category_id == category_id)
    if status:
        statement = statement.where(ActivityReport.status == status)
    if q:
        pattern = f"%{q}%"
        statement = statement.where(
            or_(
                ActivityReport.title.ilike(pattern),
                ActivityReport.input_text.ilike(pattern),
                ActivityReport.final_content.ilike(pattern),
            )
        )
    return list(db.scalars(statement.offset(skip).limit(limit)))


@router.post("", response_model=ActivityReportRead)
def create_activity_report(
    payload: ActivityReportCreate,
    db: Session = Depends(get_db),
) -> ActivityReport:
    ensure_category(db, payload.category_id)
    # TODO(Task 4): Add participant connection management.
    report = ActivityReport(**payload.model_dump())
    db.add(report)
    commit_or_400(db, "Could not create activity report")
    db.refresh(report)
    return report


@router.get("/{report_id}", response_model=ActivityReportRead)
def get_activity_report(report_id: UUID, db: Session = Depends(get_db)) -> ActivityReport:
    return get_or_404(db, ActivityReport, report_id, "Activity report")


@router.patch("/{report_id}", response_model=ActivityReportRead)
def update_activity_report(
    report_id: UUID,
    payload: ActivityReportUpdate,
    db: Session = Depends(get_db),
) -> ActivityReport:
    report = get_or_404(db, ActivityReport, report_id, "Activity report")
    data = payload.model_dump(exclude_unset=True)
    ensure_category(db, data.get("category_id"))
    apply_updates(report, payload)
    commit_or_400(db, "Could not update activity report")
    db.refresh(report)
    return report


@router.delete("/{report_id}", response_model=ActivityReportRead)
def delete_activity_report(
    report_id: UUID,
    db: Session = Depends(get_db),
) -> ActivityReport:
    report = get_or_404(db, ActivityReport, report_id, "Activity report")
    report.status = "archived"
    commit_or_400(db, "Could not archive activity report")
    db.refresh(report)
    return report


@router.get("/{report_id}/participants", response_model=list[ActivityParticipantWithMemberRead])
def get_activity_report_participants(
    report_id: UUID,
    db: Session = Depends(get_db),
) -> list[ActivityParticipant]:
    get_or_404(db, ActivityReport, report_id, "Activity report")
    stmt = (
        select(ActivityParticipant)
        .where(ActivityParticipant.activity_report_id == report_id)
        .options(selectinload(ActivityParticipant.member))
    )
    return list(db.scalars(stmt))


class ActivityFeeGeneratePayload(BaseModel):
    fee_amount: int = 10000
    period: str | None = None


@router.get("/{report_id}/detail")
def get_activity_detail(
    report_id: UUID,
    db: Session = Depends(get_db),
) -> dict:
    """Full activity detail with participants, receipts, and fee records."""
    report: ActivityReport = get_or_404(db, ActivityReport, report_id, "Activity report")

    # Participants with member info
    participants = list(db.scalars(
        select(ActivityParticipant)
        .where(ActivityParticipant.activity_report_id == report_id)
        .options(selectinload(ActivityParticipant.member))
    ))

    # Category name
    category_name: str | None = None
    if report.category_id:
        cat = db.get(ActivityCategory, report.category_id)
        category_name = cat.name if cat else None

    # Receipts
    receipts = list(db.scalars(
        select(Receipt).where(Receipt.activity_report_id == report_id)
    ))

    # Activity fee records (period encodes activity: "act-{report_id_short}")
    period_key = f"act-{str(report_id)[:8]}"
    fee_records = list(db.scalars(
        select(PaymentRecord).where(
            and_(
                PaymentRecord.period == period_key,
                PaymentRecord.payment_type == "activity_fee",
            )
        )
    ))

    # Enrich fee records with member info
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

    # Checklist
    has_participants = len(participants) > 0
    has_report = bool(report.final_content or report.generated_content)
    has_fee = fee_enabled
    fee_paid = paid_count == len(fee_records) and len(fee_records) > 0
    has_receipts = len(receipts) > 0
    receipts_ok = all(r.evidence_status == "valid" for r in receipts) if receipts else True

    checklist = [
        {"key": "participants", "label": "참여자 등록", "done": has_participants},
        {"key": "report", "label": "보고서 작성", "done": has_report},
        {"key": "activity_fee_setup", "label": "활동비 설정", "done": has_fee},
        {"key": "activity_fee_paid", "label": "활동비 납부 완료", "done": fee_paid},
        {"key": "receipts", "label": "영수증 연결", "done": has_receipts},
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


@router.post("/{report_id}/activity-fees/generate")
def generate_activity_fees(
    report_id: UUID,
    payload: ActivityFeeGeneratePayload,
    db: Session = Depends(get_db),
) -> dict:
    """Generate activity_fee PaymentRecords for all participants."""
    report: ActivityReport = get_or_404(db, ActivityReport, report_id, "Activity report")

    participants = list(db.scalars(
        select(ActivityParticipant).where(ActivityParticipant.activity_report_id == report_id)
    ))
    if not participants:
        raise HTTPException(status_code=400, detail="참여자가 없습니다. 먼저 참여자를 추가하세요.")

    period_key = payload.period or f"act-{str(report_id)[:8]}"

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
            # Don't overwrite paid/partial/exempt status
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


@router.put("/{report_id}/participants", response_model=list[ActivityParticipantWithMemberRead])
def update_activity_report_participants(
    report_id: UUID,
    payload: ParticipantsBulkUpdate,
    db: Session = Depends(get_db),
) -> list[ActivityParticipant]:
    get_or_404(db, ActivityReport, report_id, "Activity report")
    seen: set[UUID] = set()
    for p in payload.participants:
        if p.member_id in seen:
            raise HTTPException(status_code=400, detail=f"Duplicate member_id: {p.member_id}")
        seen.add(p.member_id)
        if db.get(Member, p.member_id) is None:
            raise HTTPException(status_code=404, detail=f"Member {p.member_id} not found")
    existing = list(db.scalars(
        select(ActivityParticipant).where(
            ActivityParticipant.activity_report_id == report_id
        )
    ))
    for p in existing:
        db.delete(p)
    db.flush()
    new_participants = [
        ActivityParticipant(
            activity_report_id=report_id,
            member_id=p.member_id,
            role=p.role or "participant",
        )
        for p in payload.participants
    ]
    db.add_all(new_participants)
    commit_or_400(db, "Could not update participants")
    stmt = (
        select(ActivityParticipant)
        .where(ActivityParticipant.activity_report_id == report_id)
        .options(selectinload(ActivityParticipant.member))
    )
    return list(db.scalars(stmt))

