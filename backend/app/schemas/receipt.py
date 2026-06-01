from datetime import date, datetime
from uuid import UUID

from app.schemas.common import ORMModel


class ReceiptBase(ORMModel):
    activity_report_id: UUID | None = None
    file_id: UUID | None = None
    receipt_date: date | None = None
    store_name: str | None = None
    amount: int = 0
    payment_method: str | None = None
    category: str | None = None
    evidence_status: str = "pending"
    need_check: bool = False
    reason: str | None = None


class ReceiptCreate(ReceiptBase):
    pass


class ReceiptUpdate(ORMModel):
    activity_report_id: UUID | None = None
    file_id: UUID | None = None
    receipt_date: date | None = None
    store_name: str | None = None
    amount: int | None = None
    payment_method: str | None = None
    category: str | None = None
    evidence_status: str | None = None
    need_check: bool | None = None
    reason: str | None = None


class ReceiptRead(ReceiptBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

