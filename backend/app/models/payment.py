from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.activity import ActivityReport
    from app.models.member import Member
    from app.models.transaction import BankTransaction


class PaymentRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "payment_records"
    __table_args__ = (
        UniqueConstraint(
            "member_id",
            "period",
            "payment_type",
            name="uq_payment_records_member_period_type",
        ),
    )

    member_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("members.id"),
        nullable=False,
    )
    period: Mapped[str] = mapped_column(String(50), nullable=False)
    payment_type: Mapped[str] = mapped_column(
        String(100),
        default="membership_fee",
        nullable=False,
    )
    required_amount: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    paid_amount: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="unpaid", nullable=False)
    transaction_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("bank_transactions.id"),
        nullable=True,
    )
    activity_report_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("activity_reports.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Task 21: refund fields
    refund_status: Mapped[str | None] = mapped_column(
        String(50), default="none", nullable=True
    )
    refund_amount: Mapped[int | None] = mapped_column(Integer, nullable=True)
    refund_transaction_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("bank_transactions.id", ondelete="SET NULL"),
        nullable=True,
    )
    refund_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    refunded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Membership fee policy metadata
    fee_tier: Mapped[str | None] = mapped_column(String(50), nullable=True)
    fee_rule_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    joined_term: Mapped[str | None] = mapped_column(String(50), nullable=True)
    current_term: Mapped[str | None] = mapped_column(String(50), nullable=True)
    payment_source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    manual_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    member: Mapped[Member] = relationship(back_populates="payment_records")
    transaction: Mapped[BankTransaction | None] = relationship(
        back_populates="payment_records",
        foreign_keys=[transaction_id],
    )
    refund_transaction: Mapped[BankTransaction | None] = relationship(
        back_populates="refund_payment_records",
        foreign_keys=[refund_transaction_id],
    )
    activity_report: Mapped[ActivityReport | None] = relationship()


class PaymentAdjustmentLog(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "payment_adjustment_logs"

    payment_record_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("payment_records.id", ondelete="CASCADE"),
        nullable=False,
    )
    transaction_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("bank_transactions.id", ondelete="SET NULL"),
        nullable=True,
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    previous_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    new_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    previous_paid_amount: Mapped[int | None] = mapped_column(Integer, nullable=True)
    new_paid_amount: Mapped[int | None] = mapped_column(Integer, nullable=True)
    refund_amount: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: __import__("datetime").datetime.now(__import__("datetime").timezone.utc),
    )
