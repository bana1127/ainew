from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, Date, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.activity import ActivityReport
    from app.models.file import UploadedFile


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

    activity_report: Mapped[ActivityReport | None] = relationship(
        back_populates="receipts"
    )
    file: Mapped[UploadedFile | None] = relationship(back_populates="receipts")

