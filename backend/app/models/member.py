from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Index, Integer, String, Text
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
    # Task 26-booster: member roster fields
    gender: Mapped[str | None] = mapped_column(String(20), nullable=True)
    grade: Mapped[str | None] = mapped_column(String(20), nullable=True)
    birth_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    joined_term: Mapped[str | None] = mapped_column(String(50), nullable=True)
    term_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_executive: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    role: Mapped[str | None] = mapped_column(String(100), nullable=True)

    @property
    def is_officer(self) -> bool:
        return bool(self.is_executive)

    @property
    def officer_role(self) -> str | None:
        role = (self.role or "").strip()
        if not self.is_executive and not role:
            return None
        if role in ("president", "회장"):
            return "president"
        if role in ("vice_president", "부회장"):
            return "vice_president"
        return "officer" if self.is_executive or role else None

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
