from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKeyMixin


class TransactionMatchExclusion(UUIDPrimaryKeyMixin, Base):
    """Records a transaction excluded from matching for a specific activity + payment_type scope."""
    __tablename__ = "transaction_match_exclusions"
    __table_args__ = (
        UniqueConstraint(
            "transaction_id",
            "activity_report_id",
            "payment_type",
            name="uq_tx_exclusion_tx_activity_type",
        ),
    )

    transaction_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("bank_transactions.id", ondelete="CASCADE"),
        nullable=False,
    )
    activity_report_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("activity_reports.id", ondelete="CASCADE"),
        nullable=True,
    )
    payment_type: Mapped[str] = mapped_column(String(100), nullable=False, default="activity_fee")
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: __import__("datetime").datetime.now(__import__("datetime").timezone.utc),
    )
