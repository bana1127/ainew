from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import Boolean, Date, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.activity import ActivityReport
    from app.models.file import UploadedFile
    from app.models.transaction import BankTransaction

# Supported document types
DOCUMENT_TYPE_LABELS: dict[str, str] = {
    "receipt": "영수증",
    "business_registration": "사업자등록증",
    "bankbook_copy": "통장 사본",
    "transfer_confirmation": "계좌이체 확인서",
    "invoice": "청구서",
    "quote": "견적서",
    "transaction_statement": "거래명세서",
    "other": "기타 증빙",
    "unknown": "미분류",
}


class Receipt(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "receipts"

    activity_report_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("activity_reports.id"),
        nullable=True,
    )
    file_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("uploaded_files.id"),
        nullable=True,
    )
    # Linked bank transaction (for budget correlation)
    transaction_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("bank_transactions.id", ondelete="SET NULL"),
        nullable=True,
    )
    receipt_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    store_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    amount: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    payment_method: Mapped[str | None] = mapped_column(String(100), nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    evidence_status: Mapped[str] = mapped_column(
        String(50),
        default="pending",
        nullable=False,
    )
    need_check: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Task 43: Document type expansion
    document_type: Mapped[str] = mapped_column(
        String(50), default="unknown", nullable=False
    )
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Parsed data from OCR/AI
    parsed_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    # User-edited final values (takes priority over parsed_data in display)
    manual_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    activity_report: Mapped[ActivityReport | None] = relationship(
        back_populates="receipts"
    )
    file: Mapped[UploadedFile | None] = relationship(back_populates="receipts")
    transaction: Mapped[BankTransaction | None] = relationship(
        foreign_keys=[transaction_id]
    )

