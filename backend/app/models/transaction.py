from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.member import Member
    from app.models.payment import PaymentRecord


class BankTransaction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "bank_transactions"

    transaction_datetime: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    transaction_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    memo: Mapped[str | None] = mapped_column(String(255), nullable=True)
    withdraw_amount: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    deposit_amount: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    balance: Mapped[int | None] = mapped_column(Integer, nullable=True)
    branch: Mapped[str | None] = mapped_column(String(150), nullable=True)
    raw_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    matched_member_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("members.id"),
        nullable=True,
    )
    payment_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    match_status: Mapped[str] = mapped_column(
        String(50),
        default="unmatched",
        nullable=False,
    )

    matched_member: Mapped[Member | None] = relationship(
        back_populates="bank_transactions"
    )
    payment_records: Mapped[list[PaymentRecord]] = relationship(
        back_populates="transaction"
    )

