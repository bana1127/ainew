from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
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

    member: Mapped[Member] = relationship(back_populates="payment_records")
    transaction: Mapped[BankTransaction | None] = relationship(
        back_populates="payment_records"
    )
    activity_report: Mapped[ActivityReport | None] = relationship()

