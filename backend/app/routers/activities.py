"""Activity-centric router.

ActivityReport is used as the Activity entity.
This router provides /api/activities endpoints that expose activity data
with aggregated summary fields needed by the frontend.
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.models import ActivityCategory, ActivityParticipant, ActivityReport, BankTransaction, Member
from app.models.file import UploadedFile
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
        "deleted_at": report.deleted_at.isoformat() if getattr(report, "deleted_at", None) else None,
        "created_at": report.created_at.isoformat() if report.created_at else None,
        "updated_at": report.updated_at.isoformat() if report.updated_at else None,
    }


def _get_active_activity_or_404(db: Session, activity_id: UUID) -> ActivityReport:
    report: ActivityReport = get_or_404(db, ActivityReport, activity_id, "Activity")
    if getattr(report, "deleted_at", None) is not None:
        raise HTTPException(status_code=404, detail="Activity not found")
    return report


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
    stmt = select(ActivityReport).where(ActivityReport.deleted_at.is_(None))
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
    report = _get_active_activity_or_404(db, activity_id)

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
            "refund_status": r.refund_status or "none",
            "transaction_id": str(r.transaction_id) if r.transaction_id else None,
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

    # File vault: count submission files + HWPX generated
    file_count = db.scalar(
        select(func.count(UploadedFile.id)).where(
            and_(
                UploadedFile.activity_report_id == activity_id,
                UploadedFile.deleted_at.is_(None),
            )
        )
    ) or 0
    submission_file_count = db.scalar(
        select(func.count(UploadedFile.id)).where(
            and_(
                UploadedFile.activity_report_id == activity_id,
                UploadedFile.is_submission_file.is_(True),
                UploadedFile.deleted_at.is_(None),
            )
        )
    ) or 0
    hwpx_count = db.scalar(
        select(func.count(UploadedFile.id)).where(
            and_(
                UploadedFile.activity_report_id == activity_id,
                UploadedFile.file_ext == "hwpx",
                UploadedFile.file_role == "generated",
                UploadedFile.deleted_at.is_(None),
            )
        )
    ) or 0

    checklist = [
        {"key": "participants", "label": "참여자 등록", "done": has_participants, "count": len(participants)},
        {"key": "report", "label": "보고서 작성", "done": has_report},
        {"key": "hwpx_generated", "label": "HWPX 문서 생성", "done": hwpx_count > 0, "count": hwpx_count},
        {"key": "activity_fee_setup", "label": "활동비 설정", "done": has_fee},
        {"key": "activity_fee_paid", "label": "활동비 납부 완료", "done": fee_paid,
         "detail": f"{paid_count}/{len(fee_records)}" if fee_records else None},
        {"key": "receipts", "label": "영수증 연결", "done": has_receipts, "count": len(receipts)},
        {"key": "receipts_ok", "label": "증빙 확인", "done": receipts_ok},
        {"key": "files", "label": "파일 등록", "done": file_count > 0, "count": file_count},
        {"key": "submission_files", "label": "제출용 파일 지정", "done": submission_file_count > 0,
         "count": submission_file_count},
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
            "deleted_at": report.deleted_at.isoformat() if getattr(report, "deleted_at", None) else None,
            "created_at": report.created_at.isoformat() if report.created_at else None,
            "updated_at": report.updated_at.isoformat() if report.updated_at else None,
        },
        "participants": [
            {
                "id": str(p.id),
                "member_id": str(p.member_id) if p.member_id else None,
                "name": p.member.name if p.member else p.external_name,
                "student_id": p.member.student_id if p.member else p.external_student_id,
                "department": p.member.department if p.member else p.external_affiliation,
                "role": p.role,
                "is_external": p.member_id is None,
                "external_name": p.external_name,
                "external_student_id": p.external_student_id,
                "external_affiliation": p.external_affiliation,
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
                "file_id": str(r.file_id) if r.file_id else None,
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
    report = _get_active_activity_or_404(db, activity_id)
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
    report = _get_active_activity_or_404(db, activity_id)
    report.deleted_at = datetime.now(timezone.utc)
    if report.status != "archived":
        report.status = "archived"

    # Cancel activity_fee records and unmatch linked bank transactions
    fee_records = list(db.scalars(
        select(PaymentRecord).where(
            and_(
                PaymentRecord.activity_report_id == activity_id,
                PaymentRecord.payment_type == "activity_fee",
            )
        )
    ))
    for rec in fee_records:
        if rec.status != "cancelled":
            rec.status = "cancelled"
            if (rec.paid_amount or 0) > 0:
                rec.refund_status = "refund_required"
        # Unmatch the linked bank transaction so it can be re-matched later
        if rec.transaction_id:
            txn = db.get(BankTransaction, rec.transaction_id)
            if txn:
                txn.match_status = "unmatched"
                txn.matched_member_id = None
                txn.payment_type = None
            rec.transaction_id = None

    # Clear linked_activity_id from any transactions directly linked to this activity
    for txn in db.scalars(
        select(BankTransaction).where(BankTransaction.linked_activity_id == activity_id)
    ):
        txn.linked_activity_id = None

    commit_or_400(db, "Could not delete activity")
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
    _get_active_activity_or_404(db, activity_id)
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

    # Restore cancelled activity_fee record if one exists (re-added participant)
    period_key = f"act-{str(activity_id)[:8]}"
    cancelled_fee = db.execute(
        select(PaymentRecord).where(
            and_(
                PaymentRecord.member_id == payload.member_id,
                PaymentRecord.period == period_key,
                PaymentRecord.payment_type == "activity_fee",
                PaymentRecord.activity_report_id == activity_id,
                PaymentRecord.status == "cancelled",
            )
        )
    ).scalar_one_or_none()
    if cancelled_fee:
        paid = cancelled_fee.paid_amount or 0
        required = cancelled_fee.required_amount or 0
        if paid >= required and paid > 0:
            cancelled_fee.status = "paid" if paid == required else "overpaid"
        elif paid > 0:
            cancelled_fee.status = "partial"
        else:
            cancelled_fee.status = "unpaid"
        cancelled_fee.refund_status = None

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
        "fee_record_restored": cancelled_fee is not None,
    }


@router.delete("/{activity_id}/participants/{member_id}")
def remove_participant(
    activity_id: UUID,
    member_id: UUID,
    db: Session = Depends(get_db),
) -> dict:
    _get_active_activity_or_404(db, activity_id)
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

    # Sync activity_fee PaymentRecord: cancel and flag for refund if paid
    period_key = f"act-{str(activity_id)[:8]}"
    fee_record = db.execute(
        select(PaymentRecord).where(
            and_(
                PaymentRecord.member_id == member_id,
                PaymentRecord.period == period_key,
                PaymentRecord.payment_type == "activity_fee",
                PaymentRecord.activity_report_id == activity_id,
            )
        )
    ).scalar_one_or_none()
    fee_cancelled = False
    if fee_record and fee_record.status != "cancelled":
        fee_record.status = "cancelled"
        if (fee_record.paid_amount or 0) > 0:
            fee_record.refund_status = "refund_required"
        fee_cancelled = True

    commit_or_400(db, "Could not remove participant")
    return {"ok": True, "fee_record_cancelled": fee_cancelled}


# ─── Participant Import (Task 27) ──────────────────────────────────────────────

class ParticipantImportConfirmRowPayload(BaseModel):
    row_index: int
    selected_action: str
    matched_member_id: str | None = None


class ParticipantImportConfirmPayload(BaseModel):
    action_id: str
    row_overrides: list[ParticipantImportConfirmRowPayload] = []


class ParticipantImportCancelPayload(BaseModel):
    action_id: str


@router.post("/{activity_id}/participants/import/preview")
async def preview_participant_import(
    activity_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> dict:
    """Upload participant list file → preview without modifying participants."""
    from pathlib import Path as _Path
    from app.services.activity_participant_import_service import preview_participant_import as _preview
    from app.services.file_storage_service import save_bytes_to_vault

    suffix = _Path(file.filename or "").suffix.lower()
    if suffix not in (".xls", ".xlsx", ".csv"):
        raise HTTPException(
            status_code=400,
            detail=f"지원하지 않는 파일 형식: {suffix}. 지원: .xls, .xlsx, .csv",
        )

    _get_active_activity_or_404(db, activity_id)

    file_bytes = await file.read()
    filename = file.filename or "upload"

    # Save file to vault as pending (category updated to source after confirm)
    uploaded_record = None
    try:
        uploaded_record = save_bytes_to_vault(
            db=db,
            file_bytes=file_bytes,
            original_filename=filename,
            activity_report_id=activity_id,
            file_category="activity_participant_import_pending",
            file_role="source",
        )
    except Exception:
        uploaded_record = None

    file_id = uploaded_record.id if uploaded_record else None

    try:
        result = _preview(
            db=db,
            file_bytes=file_bytes,
            filename=filename,
            activity_id=activity_id,
            file_id=file_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"파일 분석 중 오류: {e}")

    return {
        "requires_confirmation": result.requires_confirmation,
        "auto_apply": result.auto_apply,
        "activity_id": result.activity_id,
        "summary": {
            "total_rows": result.summary.total_rows,
            "matched_members": result.summary.matched_members,
            "unregistered_candidates": result.summary.unregistered_candidates,
            "duplicate_candidates": result.summary.duplicate_candidates,
            "needs_review": result.summary.needs_review,
            "invalid_rows": result.summary.invalid_rows,
            "already_participants": result.summary.already_participants,
            "will_create_participants": result.summary.will_create_participants,
            "will_update_participants": result.summary.will_update_participants,
        },
        "rows": [
            {
                "row_index": r.row_index,
                "name": r.name,
                "student_id": r.student_id,
                "department": r.department,
                "phone": r.phone,
                "match_status": r.match_status,
                "matched_member_id": r.matched_member_id,
                "matched_member_name": r.matched_member_name,
                "participant_status": r.participant_status,
                "action": r.action,
                "available_actions": r.available_actions,
                "reason": r.reason,
                "selected_action": r.selected_action,
            }
            for r in result.rows
        ],
        "confirm_payload": {"action_id": result.action_id},
    }


@router.post("/{activity_id}/participants/import/confirm")
def confirm_participant_import(
    activity_id: UUID,
    payload: ParticipantImportConfirmPayload,
    db: Session = Depends(get_db),
) -> dict:
    """Confirm and apply the pending participant import proposal."""
    from app.services.activity_participant_import_service import confirm_participant_import as _confirm

    _get_active_activity_or_404(db, activity_id)

    try:
        result = _confirm(
            db=db,
            action_id=UUID(payload.action_id),
            row_overrides=[r.model_dump() for r in payload.row_overrides],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"참여자 반영 중 오류: {e}")

    return {
        "ok": result.ok,
        "activity_id": result.activity_id,
        "result": {
            "created_participants": result.created_participants,
            "updated_participants": result.updated_participants,
            "already_participants": result.already_participants,
            "external_participants": result.external_participants,
            "ignored_rows": result.ignored_rows,
            "created_members": result.created_members,
        },
    }


@router.post("/{activity_id}/participants/import/cancel")
def cancel_participant_import(
    activity_id: UUID,
    payload: ParticipantImportCancelPayload,
    db: Session = Depends(get_db),
) -> dict:
    """Cancel a pending participant import proposal."""
    from app.services.activity_participant_import_service import cancel_participant_import as _cancel

    _get_active_activity_or_404(db, activity_id)

    try:
        _cancel(db=db, action_id=UUID(payload.action_id))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

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
    report = _get_active_activity_or_404(db, activity_id)

    participants = list(db.scalars(
        select(ActivityParticipant).where(ActivityParticipant.activity_report_id == activity_id)
    ))
    if not participants:
        raise HTTPException(status_code=400, detail="참여자가 없습니다. 먼저 참여자를 추가하세요.")

    period_key = payload.period or f"act-{str(activity_id)[:8]}"

    created = 0
    updated = 0
    for p in participants:
        if not p.member_id:
            continue  # skip external participants — no payment record
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
            # Always update required_amount so amount change is reflected everywhere
            existing.required_amount = payload.fee_amount
            if existing.status == "cancelled":
                # Participant was re-added; restore status from paid amounts
                paid = existing.paid_amount or 0
                if paid >= payload.fee_amount:
                    existing.status = "paid" if paid == payload.fee_amount else "overpaid"
                elif paid > 0:
                    existing.status = "partial"
                else:
                    existing.status = "unpaid"
                existing.refund_status = None
            elif existing.status not in ("exempt", "need_check"):
                if existing.paid_amount >= payload.fee_amount:
                    existing.status = "paid" if existing.paid_amount == payload.fee_amount else "overpaid"
                elif existing.paid_amount > 0:
                    existing.status = "partial"
                else:
                    existing.status = "unpaid"
            updated += 1
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
        "updated": updated,
        "skipped": 0,  # kept for backward compat
        "total": len(participants),
    }


# ─── Activity Fee: Transaction Matching (Task 29) ─────────────────────────────

class ActivityFeeMatchPayload(BaseModel):
    start_date: str | None = None
    end_date: str | None = None


@router.post("/{activity_id}/activity-fees/match-preview")
def activity_fee_match_preview(
    activity_id: UUID,
    payload: ActivityFeeMatchPayload = ActivityFeeMatchPayload(),
    db: Session = Depends(get_db),
) -> dict:
    """Preview transaction matching for this activity's activity_fee records only."""
    from datetime import date as _date
    from app.services.payment_matching_service import preview_payment_matching

    _get_active_activity_or_404(db, activity_id)
    period_key = f"act-{str(activity_id)[:8]}"

    start = None
    end = None
    try:
        if payload.start_date:
            start = _date.fromisoformat(payload.start_date)
        if payload.end_date:
            end = _date.fromisoformat(payload.end_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="잘못된 날짜 형식 (YYYY-MM-DD)")

    preview = preview_payment_matching(
        db=db,
        period=period_key,
        payment_type="activity_fee",
        required_amount=None,
        start_date=start,
        end_date=end,
        match_mode="auto",
        activity_id=activity_id,
    )

    from app.services.assistant_action_service import create_action_proposal
    proposal = create_action_proposal(
        db,
        action_type="payment_matching",
        source="activity_detail",
        activity_id=activity_id,
        payload={
            "period": period_key,
            "payment_type": "activity_fee",
            "required_amount": None,
            "start_date": payload.start_date,
            "end_date": payload.end_date,
            "activity_id": str(activity_id),
        },
        preview={
            "activity_id": str(activity_id),
            "period": period_key,
            "matched_count": preview.matched_count,
            "unpaid_count": preview.unpaid_count,
        },
        confidence=0.9,
        risk_level="medium",
    )

    return {
        "period": preview.period,
        "payment_type": "activity_fee",
        "activity_id": str(activity_id),
        "matched_count": preview.matched_count,
        "need_check_count": preview.need_check_count,
        "unpaid_count": preview.unpaid_count,
        "excluded_count": preview.excluded_count,
        "matched_items": [
            {
                "transaction_id": str(item.transaction_id),
                "memo": item.memo,
                "deposit_amount": item.deposit_amount,
                "matched_member_id": str(item.matched_member_id) if item.matched_member_id else None,
                "matched_member_name": item.matched_member_name,
                "match_status": item.match_status,
                "score": item.score,
                "reason": item.reason,
            }
            for item in preview.matched_items
        ],
        "need_check_items": [
            {
                "transaction_id": str(item.transaction_id),
                "memo": item.memo,
                "deposit_amount": item.deposit_amount,
                "matched_member_id": str(item.matched_member_id) if item.matched_member_id else None,
                "matched_member_name": item.matched_member_name,
                "match_status": item.match_status,
                "score": item.score,
                "reason": item.reason,
            }
            for item in preview.need_check_items
        ],
        "action_id": str(proposal.id),
    }


@router.post("/{activity_id}/activity-fees/match-apply")
def activity_fee_match_apply(
    activity_id: UUID,
    payload: ActivityFeeMatchPayload = ActivityFeeMatchPayload(),
    db: Session = Depends(get_db),
) -> dict:
    """Apply transaction matching for this activity's activity_fee records only."""
    from datetime import date as _date
    from app.services.payment_matching_service import apply_payment_matching

    _get_active_activity_or_404(db, activity_id)
    period_key = f"act-{str(activity_id)[:8]}"

    start = None
    end = None
    try:
        if payload.start_date:
            start = _date.fromisoformat(payload.start_date)
        if payload.end_date:
            end = _date.fromisoformat(payload.end_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="잘못된 날짜 형식 (YYYY-MM-DD)")

    result = apply_payment_matching(
        db=db,
        period=period_key,
        payment_type="activity_fee",
        required_amount=None,
        start_date=start,
        end_date=end,
        match_mode="auto",
        activity_id=activity_id,
    )

    return {
        "ok": True,
        "activity_id": str(activity_id),
        "period": period_key,
        "payment_type": "activity_fee",
        "matched_count": result.matched_count,
        "created_payment_records": result.created_payment_records,
        "updated_payment_records": result.updated_payment_records,
        "updated_transactions": result.updated_transactions,
    }


# ─── Activity Fee: Proposal-based Transaction Matching (Task 30) ──────────────

class ActivityFeeMatchTransactionsConfirmPayload(BaseModel):
    action_id: str
    confirmed_row_ids: list[str] | None = None


class ActivityFeeMatchTransactionsCancelPayload(BaseModel):
    action_id: str


@router.post("/{activity_id}/activity-fees/match-transactions-preview")
def activity_fee_match_transactions_preview(
    activity_id: UUID,
    db: Session = Depends(get_db),
) -> dict:
    """Preview transaction matching — no DB changes. Returns proposal action_id for confirm."""
    from app.services.activity_fee_transaction_matching_service import (
        preview_activity_fee_transaction_matching,
    )

    _get_active_activity_or_404(db, activity_id)

    try:
        result = preview_activity_fee_transaction_matching(db=db, activity_id=activity_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"매칭 분석 중 오류: {e}")

    return {
        "activity_id": result.activity_id,
        "requires_confirmation": result.requires_confirmation,
        "auto_apply": result.auto_apply,
        "summary": {
            "total_transactions": result.summary.total_transactions,
            "auto_match_candidates": result.summary.auto_match_candidates,
            "amount_mismatch": result.summary.amount_mismatch,
            "name_check_required": result.summary.name_check_required,
            "already_paid": result.summary.already_paid,
            "already_matched": result.summary.already_matched,
            "unmatched": result.summary.unmatched,
            "excluded_transactions": result.summary.excluded_transactions,
        },
        "rows": [
            {
                "transaction_id": r.transaction_id,
                "transaction_datetime": r.transaction_datetime,
                "memo": r.memo,
                "deposit_amount": r.deposit_amount,
                "matched_member_id": r.matched_member_id,
                "matched_member_name": r.matched_member_name,
                "payment_record_id": r.payment_record_id,
                "required_amount": r.required_amount,
                "amount_difference": r.amount_difference,
                "match_status": r.match_status,
                "score": r.score,
                "reason": r.reason,
            }
            for r in result.rows
        ],
        "confirm_payload": {"action_id": result.action_id},
    }


@router.post("/{activity_id}/activity-fees/match-transactions-confirm")
def activity_fee_match_transactions_confirm(
    activity_id: UUID,
    payload: ActivityFeeMatchTransactionsConfirmPayload,
    db: Session = Depends(get_db),
) -> dict:
    """Confirm and apply the matching proposal.

    Only auto_match_candidate rows are applied by default.
    Pass confirmed_row_ids to selectively apply specific transaction_ids.
    """
    from app.services.activity_fee_transaction_matching_service import (
        confirm_activity_fee_transaction_matching,
    )

    _get_active_activity_or_404(db, activity_id)

    try:
        result = confirm_activity_fee_transaction_matching(
            db=db,
            action_id=UUID(payload.action_id),
            confirmed_row_ids=payload.confirmed_row_ids,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"매칭 적용 중 오류: {e}")

    return {
        "ok": result.ok,
        "activity_id": result.activity_id,
        "matched_count": result.matched_count,
        "skipped_count": result.skipped_count,
        "updated_payment_records": result.updated_payment_records,
        "updated_transactions": result.updated_transactions,
    }


@router.post("/{activity_id}/activity-fees/match-transactions-cancel")
def activity_fee_match_transactions_cancel(
    activity_id: UUID,
    payload: ActivityFeeMatchTransactionsCancelPayload,
    db: Session = Depends(get_db),
) -> dict:
    """Cancel a pending matching proposal."""
    from app.services.activity_fee_transaction_matching_service import (
        cancel_activity_fee_transaction_matching,
    )

    _get_active_activity_or_404(db, activity_id)

    try:
        cancel_activity_fee_transaction_matching(db=db, action_id=UUID(payload.action_id))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"ok": True}


# ─── File Vault ───────────────────────────────────────────────────────────────

@router.get("/{activity_id}/files")
def list_activity_files(
    activity_id: UUID,
    category: str | None = None,
    role: str | None = None,
    include_deleted: bool = False,
    db: Session = Depends(get_db),
) -> list[dict]:
    _get_active_activity_or_404(db, activity_id)
    stmt = select(UploadedFile).where(UploadedFile.activity_report_id == activity_id)
    if category:
        stmt = stmt.where(UploadedFile.file_category == category)
    if role:
        stmt = stmt.where(UploadedFile.file_role == role)
    if not include_deleted:
        stmt = stmt.where(UploadedFile.deleted_at.is_(None))
    stmt = stmt.order_by(UploadedFile.created_at.desc())
    from app.routers.files import _file_to_dict  # local import to avoid circular
    return [_file_to_dict(f) for f in db.scalars(stmt)]


@router.post("/{activity_id}/files")
def upload_activity_file(
    activity_id: UUID,
    file: UploadFile = File(...),
    file_category: str | None = Form(default=None),
    file_role: str | None = Form(default=None),
    is_submission_file: bool = Form(default=False),
    submission_month: str | None = Form(default=None),
    db: Session = Depends(get_db),
) -> dict:
    _get_active_activity_or_404(db, activity_id)
    from app.services.file_storage_service import save_activity_file
    from app.routers.files import _file_to_dict
    record = save_activity_file(
        file=file,
        db=db,
        activity_report_id=activity_id,
        file_category=file_category,
        file_role=file_role,
        is_submission_file=is_submission_file,
        submission_month=submission_month,
    )
    return _file_to_dict(record)


# ─── Document Generation (Task 20) ────────────────────────────────────────────

class DocumentPreviewPayload(BaseModel):
    template_id: str
    overrides: dict[str, str] = {}


class DocumentGeneratePayload(BaseModel):
    template_id: str
    document_title: str | None = None
    overrides: dict[str, str] = {}
    mark_as_submission: bool = False
    submission_month: str | None = None


@router.post("/{activity_id}/documents/preview")
def preview_document(
    activity_id: UUID,
    payload: DocumentGeneratePayload,
    db: Session = Depends(get_db),
) -> dict:
    _get_active_activity_or_404(db, activity_id)
    from uuid import UUID as _UUID
    tpl_file = db.get(UploadedFile, _UUID(payload.template_id))
    if not tpl_file or tpl_file.file_category != "document_template":
        raise HTTPException(status_code=404, detail="Template not found")

    from app.services.file_storage_service import resolve_abs_path
    from app.services.hwpx_generation_service import (
        build_generation_context,
        build_preview_mappings,
    )

    template_abs = resolve_abs_path(tpl_file)

    ctx = build_generation_context(db, activity_id, payload.overrides or {})
    report = _get_active_activity_or_404(db, activity_id)

    mode, mappings, warnings = build_preview_mappings(template_abs, ctx)

    # Back-compat: also provide mapped_fields dict
    mapped_fields = {m["field"]: m["target"] for m in mappings if m.get("field")}

    return {
        "activity_id": str(activity_id),
        "template_id": payload.template_id,
        "mode": mode,
        "mappings": mappings,
        "warnings": warnings,
        "mapped_fields": mapped_fields,
        "missing_fields": [],
        "content_preview": {
            "title": report.title,
            "body": ctx.report_body[:200] if ctx.report_body else "",
        },
    }


@router.post("/{activity_id}/documents/generate")
def generate_document(
    activity_id: UUID,
    payload: DocumentGeneratePayload,
    db: Session = Depends(get_db),
) -> dict:
    report = _get_active_activity_or_404(db, activity_id)
    from uuid import UUID as _UUID
    tpl_file = db.get(UploadedFile, _UUID(payload.template_id))
    if not tpl_file or tpl_file.file_category != "document_template":
        raise HTTPException(status_code=404, detail="Template not found")

    ext = tpl_file.file_ext or "hwpx"
    if ext != "hwpx":
        raise HTTPException(
            status_code=400,
            detail="HWPX(.hwpx) 파일만 자동 생성을 지원합니다. HWP는 원본 다운로드를 사용하세요.",
        )

    from app.services.file_storage_service import resolve_abs_path
    from app.services.hwpx_generation_service import (
        build_generation_context,
        generate_hwpx,
    )

    template_abs = resolve_abs_path(tpl_file)
    if not template_abs.exists():
        raise HTTPException(status_code=404, detail="템플릿 파일을 찾을 수 없습니다.")

    ctx = build_generation_context(db, activity_id, payload.overrides or {})

    # Build output path
    from uuid import uuid4 as _uuid4
    from pathlib import Path as _Path
    doc_title = payload.document_title or f"{report.title}_{report.activity_date or 'doc'}"
    safe_title = doc_title.replace("/", "_").replace("\\", "_")[:60]
    out_filename = f"{safe_title}.hwpx"
    stored_name = f"{_uuid4()}.hwpx"

    from app.core.config import settings as _settings
    out_dir = _settings.UPLOAD_DIR / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    output_abs = out_dir / stored_name

    try:
        result = generate_hwpx(template_abs, output_abs, ctx)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"HWPX 생성 중 오류: {exc}")

    size_bytes = output_abs.stat().st_size if output_abs.exists() else 0
    try:
        rel_path = output_abs.relative_to(_settings.UPLOAD_DIR.parent)
    except ValueError:
        rel_path = _Path("uploads") / "generated" / stored_name

    from app.routers.common import commit_or_400 as _commit
    gen_file = UploadedFile(
        original_filename=out_filename,
        stored_path=rel_path.as_posix(),
        stored_filename=stored_name,
        mime_type="application/x-hwpml",
        file_ext="hwpx",
        size_bytes=size_bytes,
        file_type="activity_report",
        file_category="activity_report",
        file_role="generated",
        is_submission_file=payload.mark_as_submission,
        submission_month=payload.submission_month,
        activity_report_id=activity_id,
        preview_status="pending",
        preview_metadata_json={
            "template_id": payload.template_id,
            "template_name": (tpl_file.preview_metadata_json or {}).get("template_name"),
            "document_title": doc_title,
            "mode": result.mode,
            "replaced_count": result.replaced_count,
            "participant_count": result.participant_count,
            "mapped_fields": result.mapped_fields,
            "missing_fields": result.missing_fields,
            "warnings": result.warnings,
        },
    )
    db.add(gen_file)
    _commit(db, "Could not save generated document")
    db.refresh(gen_file)

    return {
        "ok": True,
        "file_id": str(gen_file.id),
        "generated_file_id": str(gen_file.id),
        "download_url": f"/api/files/{gen_file.id}/download",
        "missing_fields": result.missing_fields,
        "activity_id": str(activity_id),
        "mode": result.mode,
        "replaced_count": result.replaced_count,
        "participant_count": result.participant_count,
        "warnings": result.warnings,
    }


@router.get("/{activity_id}/documents")
def list_activity_documents(
    activity_id: UUID,
    db: Session = Depends(get_db),
) -> list[dict]:
    _get_active_activity_or_404(db, activity_id)
    stmt = select(UploadedFile).where(
        and_(
            UploadedFile.activity_report_id == activity_id,
            UploadedFile.file_role == "generated",
            UploadedFile.deleted_at.is_(None),
        )
    ).order_by(UploadedFile.created_at.desc())

    docs = []
    for f in db.scalars(stmt):
        meta = f.preview_metadata_json or {}
        docs.append({
            "id": str(f.id),
            "file_id": str(f.id),
            "template_name": meta.get("template_name") or "",
            "title": f.original_filename,
            "document_title": meta.get("document_title") or f.original_filename,
            "missing_fields": meta.get("missing_fields") or [],
            "is_submission_file": f.is_submission_file,
            "submission_month": f.submission_month,
            "created_at": f.created_at.isoformat() if f.created_at else None,
            "download_url": f"/api/files/{f.id}/download",
        })
    return docs


@router.patch("/{activity_id}/activity-fees/{record_id}")
def update_activity_fee_record(
    activity_id: UUID,
    record_id: UUID,
    payload: dict,
    db: Session = Depends(get_db),
) -> dict:
    _get_active_activity_or_404(db, activity_id)
    record = db.get(PaymentRecord, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Payment record not found")

    # Scope guard: only activity_fee records for this activity
    if record.payment_type != "activity_fee":
        raise HTTPException(status_code=400, detail="Only activity_fee records can be updated via this endpoint")
    if record.activity_report_id != activity_id:
        raise HTTPException(status_code=400, detail="Record does not belong to this activity")

    allowed = {"paid_amount", "status", "required_amount", "refund_status"}
    for key, val in payload.items():
        if key in allowed:
            setattr(record, key, val)

    if "paid_amount" in payload and "status" not in payload:
        if record.paid_amount == 0:
            record.status = "unpaid"
        elif record.paid_amount < record.required_amount:
            record.status = "partial"
        elif record.paid_amount == record.required_amount:
            record.status = "paid"
        else:
            record.status = "overpaid"

    commit_or_400(db, "Could not update payment record")
    db.refresh(record)
    return {
        "id": str(record.id),
        "member_id": str(record.member_id),
        "required_amount": record.required_amount,
        "paid_amount": record.paid_amount,
        "status": record.status,
        "period": record.period,
        "member_name": None,
        "student_id": None,
        "refund_status": record.refund_status or "none",
        "transaction_id": str(record.transaction_id) if record.transaction_id else None,
    }


# ─── Activity Fee: Summary ────────────────────────────────────────────────────

@router.get("/{activity_id}/activity-fees/summary")
def get_activity_fee_summary(
    activity_id: UUID,
    db: Session = Depends(get_db),
) -> dict:
    """Aggregated summary of activity_fee records for this activity only."""
    _get_active_activity_or_404(db, activity_id)
    period_key = f"act-{str(activity_id)[:8]}"
    fee_records = list(db.scalars(
        select(PaymentRecord).where(
            and_(
                PaymentRecord.period == period_key,
                PaymentRecord.payment_type == "activity_fee",
            )
        )
    ))
    paid = sum(1 for r in fee_records if r.status == "paid")
    unpaid = sum(1 for r in fee_records if r.status == "unpaid")
    partial = sum(1 for r in fee_records if r.status == "partial")
    overpaid = sum(1 for r in fee_records if r.status == "overpaid")
    refund_needed = sum(
        1 for r in fee_records
        if r.refund_status in ("refund_required", "refund_pending")
    )
    total_required = sum(r.required_amount for r in fee_records)
    total_paid = sum(r.paid_amount for r in fee_records)
    return {
        "activity_id": str(activity_id),
        "period_key": period_key,
        "participant_count": len(fee_records),
        "paid": paid,
        "unpaid": unpaid,
        "partial": partial,
        "overpaid": overpaid,
        "refund_needed": refund_needed,
        "total_required": total_required,
        "total_paid": total_paid,
    }


# ─── Activity Fee: Scoped Unmatch ─────────────────────────────────────────────

class ActivityFeeUnmatchPayload(BaseModel):
    keep_paid_amount: bool = True


@router.post("/{activity_id}/activity-fees/{record_id}/unmatch")
def unmatch_activity_fee_record(
    activity_id: UUID,
    record_id: UUID,
    payload: ActivityFeeUnmatchPayload = ActivityFeeUnmatchPayload(),
    db: Session = Depends(get_db),
) -> dict:
    """Cancel the transaction match for an activity_fee record (scoped to this activity)."""
    from app.models import BankTransaction
    _get_active_activity_or_404(db, activity_id)
    record = db.get(PaymentRecord, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Payment record not found")

    # Scope guard
    if record.payment_type != "activity_fee":
        raise HTTPException(status_code=400, detail="Only activity_fee records can be unmatched via this endpoint")
    if record.activity_report_id != activity_id:
        raise HTTPException(status_code=400, detail="Record does not belong to this activity")

    # Revert linked transaction
    if record.transaction_id:
        txn = db.get(BankTransaction, record.transaction_id)
        if txn:
            txn.match_status = "unmatched"
            txn.matched_member_id = None

    record.transaction_id = None

    if not payload.keep_paid_amount:
        record.paid_amount = 0
        record.status = "unpaid"
    else:
        # Recalculate status based on current paid_amount
        if record.paid_amount == 0:
            record.status = "unpaid"
        elif record.paid_amount < record.required_amount:
            record.status = "partial"
        elif record.paid_amount == record.required_amount:
            record.status = "paid"
        else:
            record.status = "overpaid"

    commit_or_400(db, "Could not unmatch payment record")
    db.refresh(record)
    return {
        "ok": True,
        "payment_record_id": str(record.id),
        "status": record.status,
        "paid_amount": record.paid_amount,
        "transaction_id": None,
    }


# ─── Activity Fee: Transaction Exclusion (Task 32) ────────────────────────────

class TransactionExcludePayload(BaseModel):
    reason: str | None = None


@router.post("/{activity_id}/activity-fees/transactions/{transaction_id}/exclude")
def exclude_activity_fee_transaction(
    activity_id: UUID,
    transaction_id: UUID,
    payload: TransactionExcludePayload = TransactionExcludePayload(),
    db: Session = Depends(get_db),
) -> dict:
    """Exclude a transaction from this activity's activity_fee matching preview.

    Scope is (transaction_id, activity_id, payment_type=activity_fee) only.
    Does not affect membership_fee matching or other activities.
    """
    from app.models import BankTransaction
    from app.models.transaction_match_exclusion import TransactionMatchExclusion

    _get_active_activity_or_404(db, activity_id)

    txn = db.get(BankTransaction, transaction_id)
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    existing = db.scalar(
        select(TransactionMatchExclusion).where(
            and_(
                TransactionMatchExclusion.transaction_id == transaction_id,
                TransactionMatchExclusion.activity_report_id == activity_id,
                TransactionMatchExclusion.payment_type == "activity_fee",
            )
        )
    )

    if existing:
        # Reactivate if was previously deactivated
        if not existing.is_active:
            existing.is_active = True
            existing.reason = payload.reason or existing.reason
            db.commit()
        return {
            "ok": True,
            "id": str(existing.id),
            "transaction_id": str(transaction_id),
            "activity_id": str(activity_id),
            "payment_type": "activity_fee",
            "is_active": True,
            "created": False,
        }

    exclusion = TransactionMatchExclusion(
        transaction_id=transaction_id,
        activity_report_id=activity_id,
        payment_type="activity_fee",
        reason=payload.reason,
        is_active=True,
    )
    db.add(exclusion)
    commit_or_400(db, "Could not create exclusion")
    db.refresh(exclusion)
    return {
        "ok": True,
        "id": str(exclusion.id),
        "transaction_id": str(transaction_id),
        "activity_id": str(activity_id),
        "payment_type": "activity_fee",
        "is_active": True,
        "created": True,
    }


@router.post("/{activity_id}/activity-fees/transactions/{transaction_id}/include")
def include_activity_fee_transaction(
    activity_id: UUID,
    transaction_id: UUID,
    db: Session = Depends(get_db),
) -> dict:
    """Remove exclusion so a transaction re-appears in this activity's matching preview."""
    from app.models.transaction_match_exclusion import TransactionMatchExclusion

    _get_active_activity_or_404(db, activity_id)

    exclusion = db.scalar(
        select(TransactionMatchExclusion).where(
            and_(
                TransactionMatchExclusion.transaction_id == transaction_id,
                TransactionMatchExclusion.activity_report_id == activity_id,
                TransactionMatchExclusion.payment_type == "activity_fee",
                TransactionMatchExclusion.is_active.is_(True),
            )
        )
    )

    if not exclusion:
        raise HTTPException(status_code=404, detail="No active exclusion found for this transaction")

    exclusion.is_active = False
    db.commit()
    return {
        "ok": True,
        "transaction_id": str(transaction_id),
        "activity_id": str(activity_id),
        "payment_type": "activity_fee",
        "is_active": False,
    }


@router.get("/{activity_id}/activity-fees/excluded-transactions")
def list_excluded_transactions(
    activity_id: UUID,
    db: Session = Depends(get_db),
) -> list[dict]:
    """List transactions excluded from this activity's activity_fee matching."""
    from app.models import BankTransaction
    from app.models.transaction_match_exclusion import TransactionMatchExclusion

    _get_active_activity_or_404(db, activity_id)

    exclusions = list(db.scalars(
        select(TransactionMatchExclusion).where(
            and_(
                TransactionMatchExclusion.activity_report_id == activity_id,
                TransactionMatchExclusion.payment_type == "activity_fee",
                TransactionMatchExclusion.is_active.is_(True),
            )
        ).order_by(TransactionMatchExclusion.created_at.desc())
    ))

    result = []
    for excl in exclusions:
        txn = db.get(BankTransaction, excl.transaction_id)
        result.append({
            "exclusion_id": str(excl.id),
            "transaction_id": str(excl.transaction_id),
            "activity_id": str(activity_id),
            "payment_type": excl.payment_type,
            "reason": excl.reason,
            "created_at": excl.created_at.isoformat() if excl.created_at else None,
            "transaction": {
                "id": str(txn.id),
                "memo": txn.memo,
                "deposit_amount": int(txn.deposit_amount or 0),
                "transaction_datetime": txn.transaction_datetime.isoformat() if txn.transaction_datetime else None,
            } if txn else None,
        })
    return result


# ─── Audit Checklist (Task 34) ────────────────────────────────────────────────

@router.get("/{activity_id}/audit-checklist")
def get_audit_checklist(
    activity_id: UUID,
    db: Session = Depends(get_db),
) -> dict:
    """Return a detailed audit readiness checklist for the activity."""
    from app.services.activity_audit_check_service import compute_audit_checklist

    _get_active_activity_or_404(db, activity_id)

    try:
        result = compute_audit_checklist(db, activity_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {
        "activity_id": result.activity_id,
        "activity_title": result.activity_title,
        "total_done": result.total_done,
        "total_items": result.total_items,
        "ready_for_audit": result.ready_for_audit,
        "items": [
            {
                "key": item.key,
                "label": item.label,
                "done": item.done,
                "detail": item.detail,
                "count": item.count,
                "warning": item.warning,
            }
            for item in result.items
        ],
    }

