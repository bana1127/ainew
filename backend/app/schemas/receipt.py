from datetime import date, datetime
from typing import Any
from uuid import UUID

from app.schemas.common import ORMModel

VALID_DOCUMENT_TYPES = {
    "receipt", "business_registration", "bankbook_copy",
    "transfer_confirmation", "invoice", "quote",
    "transaction_statement", "activity_photo", "other", "unknown",
}


class ReceiptBase(ORMModel):
    activity_report_id: UUID | None = None
    file_id: UUID | None = None
    transaction_id: UUID | None = None
    receipt_date: date | None = None
    store_name: str | None = None
    amount: int | None = 0
    payment_method: str | None = None
    category: str | None = None
    evidence_status: str = "pending"
    need_check: bool = False
    reason: str | None = None
    document_type: str = "unknown"
    title: str | None = None
    parsed_data: dict[str, Any] | None = None
    manual_data: dict[str, Any] | None = None


class ReceiptCreate(ReceiptBase):
    pass


class ReceiptUpdate(ORMModel):
    activity_report_id: UUID | None = None
    file_id: UUID | None = None
    transaction_id: UUID | None = None
    receipt_date: date | None = None
    store_name: str | None = None
    amount: int | None = None
    payment_method: str | None = None
    category: str | None = None
    evidence_status: str | None = None
    need_check: bool | None = None
    reason: str | None = None
    document_type: str | None = None
    title: str | None = None
    parsed_data: dict[str, Any] | None = None
    manual_data: dict[str, Any] | None = None


class ReceiptRead(ReceiptBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
