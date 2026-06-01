from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import BankTransaction, Member, PaymentRecord
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


def _auto_status(paid: int, required: int, explicit: str | None) -> str:
    """Compute status from amounts unless user supplied an explicit value."""
    if explicit:
        return explicit
    if required <= 0:
        return "unpaid"
    if paid >= required:
        return "paid"
    if paid > 0:
        return "partial"
    return "unpaid"


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


def _enrich(record: PaymentRecord, member: Member | None) -> PaymentRecordRead:
    """Build a PaymentRecordRead with member info attached."""
    data = PaymentRecordRead.model_validate(record)
    if member:
        data.member_name = member.name
        data.student_id = member.student_id
        data.department = member.department
    return data


@router.get("", response_model=list[PaymentRecordRead])
def list_payment_records(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
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

    return [_enrich(r, members_map.get(r.member_id)) for r in records]


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
    return _enrich(record, member)


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
    return _enrich(record, member)


@router.delete("/{payment_id}", response_model=PaymentRecordRead)
def delete_payment_record(
    payment_id: UUID,
    db: Session = Depends(get_db),
) -> PaymentRecordRead:
    record = get_or_404(db, PaymentRecord, payment_id, "Payment record")
    member = db.get(Member, record.member_id)
    enriched = _enrich(record, member)
    db.delete(record)
    commit_or_400(db, "Could not delete payment record")
    return enriched


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
        commit_or_400(db, "Could not update payment record")
        db.refresh(existing)
        return _enrich(existing, member)
    else:
        record = PaymentRecord(
            member_id=payload.member_id,
            period=payload.period,
            payment_type=payload.payment_type,
            required_amount=payload.required_amount,
            paid_amount=paid_amount,
            status=status,
        )
        db.add(record)
        commit_or_400(db, "Could not create payment record")
        db.refresh(record)
        return _enrich(record, member)
