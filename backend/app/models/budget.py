from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.transaction import BankTransaction


class BudgetCategory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "budget_categories"
    __table_args__ = (
        UniqueConstraint("name", "type", name="uq_budget_categories_name_type"),
    )

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    parent_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("budget_categories.id", ondelete="SET NULL"),
        nullable=True,
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    parent: Mapped[BudgetCategory | None] = relationship(
        remote_side="BudgetCategory.id",
        back_populates="children",
    )
    children: Mapped[list[BudgetCategory]] = relationship(back_populates="parent")
    plans: Mapped[list[BudgetPlan]] = relationship(back_populates="category")
    transactions: Mapped[list[BankTransaction]] = relationship(back_populates="budget_category")


class BudgetPlan(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "budget_plans"
    __table_args__ = (
        UniqueConstraint("period", "category_id", name="uq_budget_plans_period_category"),
    )

    period: Mapped[str] = mapped_column(String(50), nullable=False)
    category_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("budget_categories.id", ondelete="CASCADE"),
        nullable=False,
    )
    planned_amount: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    category: Mapped[BudgetCategory] = relationship(back_populates="plans")
