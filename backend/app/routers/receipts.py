from datetime import datetime as dt_type
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import ActivityReport, Receipt
from app.routers.common import apply_updates, commit_or_400, get_or_404
from app.schemas import ReceiptCreate, ReceiptRead, ReceiptUpdate
from app.services.quarter_service import quarter_date_range_from_str


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
    document_type: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    operating_quarter: str | None = Query(default=None, description="운영 분기 (예: 2026-Q2)"),
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
    if document_type:
        statement = statement.where(Receipt.document_type == document_type)
    if operating_quarter:
        try:
            q_start, q_end = quarter_date_range_from_str(operating_quarter)
            statement = statement.where(Receipt.receipt_date >= q_start)
            statement = statement.where(Receipt.receipt_date <= q_end)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
    else:
        if start_date:
            statement = statement.where(Receipt.receipt_date >= dt_type.fromisoformat(start_date).date())
        if end_date:
            statement = statement.where(Receipt.receipt_date <= dt_type.fromisoformat(end_date).date())
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
    """Link or unlink a receipt to an activity.

    Also syncs the linked UploadedFile so the receipt image appears in the
    activity file vault (증빙/파일함).
    """
    from app.models.file import UploadedFile

    receipt = get_or_404(db, Receipt, receipt_id, "Receipt")
    if payload.activity_report_id is not None:
        if db.get(ActivityReport, payload.activity_report_id) is None:
            raise HTTPException(status_code=404, detail="Activity not found")

    receipt.activity_report_id = payload.activity_report_id

    # Sync UploadedFile so it appears in the activity file vault
    if receipt.file_id:
        uploaded_file = db.get(UploadedFile, receipt.file_id)
        if uploaded_file:
            uploaded_file.activity_report_id = payload.activity_report_id
            if payload.activity_report_id:
                uploaded_file.file_category = "receipt"
                uploaded_file.file_role = "evidence"
                uploaded_file.related_entity_type = "activity_report"
                uploaded_file.related_entity_id = payload.activity_report_id
            else:
                # Unlinking: clear activity-specific context
                uploaded_file.related_entity_type = None
                uploaded_file.related_entity_id = None

    commit_or_400(db, "Could not update receipt activity link")
    db.refresh(receipt)
    return receipt


# ── Task 43: Manual data edit endpoint ───────────────────────────────────────

class ReceiptManualDataPayload(BaseModel):
    manual_data: dict[str, Any]
    document_type: str | None = None
    title: str | None = None
    amount: int | None = None
    receipt_date: str | None = None


@router.patch("/{receipt_id}/manual-edit", response_model=ReceiptRead)
def manual_edit_receipt(
    receipt_id: UUID,
    payload: ReceiptManualDataPayload,
    db: Session = Depends(get_db),
) -> Receipt:
    """사용자가 증빙의 parsed_data를 수정 → manual_data에 저장.

    화면에는 manual_data가 있으면 우선 표시됩니다.
    """
    from datetime import date as date_type

    receipt = get_or_404(db, Receipt, receipt_id, "Receipt")
    receipt.manual_data = payload.manual_data
    if payload.document_type is not None:
        receipt.document_type = payload.document_type
    if payload.title is not None:
        receipt.title = payload.title
    if payload.amount is not None:
        receipt.amount = payload.amount
    if payload.receipt_date is not None:
        try:
            receipt.receipt_date = date_type.fromisoformat(payload.receipt_date)
        except ValueError:
            pass
    commit_or_400(db, "Could not save manual edit")
    db.refresh(receipt)
    return receipt


@router.post("/manual", response_model=ReceiptRead)
def create_manual_receipt(
    payload: ReceiptCreate,
    db: Session = Depends(get_db),
) -> Receipt:
    """파일 없이 수동 증빙 추가."""
    receipt = Receipt(**payload.model_dump())
    if not receipt.document_type:
        receipt.document_type = "other"
    db.add(receipt)
    commit_or_400(db, "Could not create manual receipt")
    db.refresh(receipt)
    return receipt

