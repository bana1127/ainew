from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.activity import ActivityParticipant
    from app.models.payment import PaymentRecord
    from app.models.transaction import BankTransaction


class Member(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "members"
    __table_args__ = (
        Index("ix_members_name", "name"),
        Index("ix_members_student_id", "student_id"),
        Index("ix_members_status", "status"),
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    student_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    department: Mapped[str | None] = mapped_column(String(100), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)
    memo: Mapped[str | None] = mapped_column(Text, nullable=True)

    activity_participants: Mapped[list[ActivityParticipant]] = relationship(
        back_populates="member",
        cascade="all, delete-orphan",
    )
    bank_transactions: Mapped[list[BankTransaction]] = relationship(
        back_populates="matched_member"
    )
    payment_records: Mapped[list[PaymentRecord]] = relationship(
        back_populates="member",
        cascade="all, delete-orphan",
    )

