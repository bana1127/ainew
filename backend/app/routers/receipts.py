from datetime import datetime as dt_type
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import ActivityReport, Receipt
from app.routers.common import apply_updates, commit_or_400, get_or_404
from app.schemas import ReceiptCreate, ReceiptRead, ReceiptUpdate


router = APIRouter()


@router.get("", response_model=list[ReceiptRead])
def list_receipts(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    activity_report_id: UUID | None = None,
    evidence_status: str | None = None,
    need_check: bool | None = None,
    payment_method: str | None = None,
    category: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
) -> list[Receipt]:
    statement = select(Receipt)
    if activity_report_id:
        statement = statement.where(Receipt.activity_report_id == activity_report_id)
    if evidence_status:
        statement = statement.where(Receipt.evidence_status == evidence_status)
    if need_check is not None:
        statement = statement.where(Receipt.need_check.is_(need_check))
    if payment_method:
        statement = statement.where(Receipt.payment_method == payment_method)
    if category:
        statement = statement.where(Receipt.category == category)
    if start_date:
        statement = statement.where(Receipt.purchased_at >= dt_type.fromisoformat(start_date))
    if end_date:
        statement = statement.where(Receipt.purchased_at <= dt_type.fromisoformat(end_date))
    if q:
        like = f"%{q}%"
        statement = statement.where(
            or_(
                Receipt.store_name.ilike(like),
                Receipt.reason.ilike(like),
                Receipt.category.ilike(like),
                Receipt.payment_method.ilike(like),
            )
        )
    return list(db.scalars(statement.offset(skip).limit(limit)))


@router.post("", response_model=ReceiptRead)
def create_receipt(payload: ReceiptCreate, db: Session = Depends(get_db)) -> Receipt:
    # TODO(Task 4+): Add OCR analysis and evidence validation workflow.
    receipt = Receipt(**payload.model_dump())
    db.add(receipt)
    commit_or_400(db, "Could not create receipt")
    db.refresh(receipt)
    return receipt


@router.get("/{receipt_id}", response_model=ReceiptRead)
def get_receipt(receipt_id: UUID, db: Session = Depends(get_db)) -> Receipt:
    return get_or_404(db, Receipt, receipt_id, "Receipt")


@router.patch("/{receipt_id}", response_model=ReceiptRead)
def update_receipt(
    receipt_id: UUID,
    payload: ReceiptUpdate,
    db: Session = Depends(get_db),
) -> Receipt:
    receipt = get_or_404(db, Receipt, receipt_id, "Receipt")
    apply_updates(receipt, payload)
    commit_or_400(db, "Could not update receipt")
    db.refresh(receipt)
    return receipt


@router.delete("/{receipt_id}", response_model=ReceiptRead)
def delete_receipt(receipt_id: UUID, db: Session = Depends(get_db)) -> Receipt:
    receipt = get_or_404(db, Receipt, receipt_id, "Receipt")
    db.delete(receipt)
    commit_or_400(db, "Could not delete receipt")
    return receipt


class ReceiptActivityLink(BaseModel):
    activity_report_id: UUID | None = None


@router.patch("/{receipt_id}/activity", response_model=ReceiptRead)
def link_receipt_to_activity(
    receipt_id: UUID,
    payload: ReceiptActivityLink,
    db: Session = Depends(get_db),
) -> Receipt:
    """Link or unlink a receipt to an activity (activity_report)."""
    receipt = get_or_404(db, Receipt, receipt_id, "Receipt")
    if payload.activity_report_id is not None:
        if db.get(ActivityReport, payload.activity_report_id) is None:
            raise HTTPException(status_code=404, detail="Activity not found")
    receipt.activity_report_id = payload.activity_report_id
    commit_or_400(db, "Could not update receipt activity link")
    db.refresh(receipt)
    return receipt

