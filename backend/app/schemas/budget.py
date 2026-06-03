from __future__ import annotations

from datetime import datetime
from uuid import UUID

from app.schemas.common import ORMModel


class BudgetCategoryCreate(ORMModel):
    name: str
    type: str
    parent_id: UUID | None = None
    sort_order: int = 0
    is_active: bool = True


class BudgetCategoryUpdate(ORMModel):
    name: str | None = None
    type: str | None = None
    parent_id: UUID | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class BudgetCategoryRead(ORMModel):
    id: UUID
    name: str
    type: str
    parent_id: UUID | None = None
    sort_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class BudgetPlanCreate(ORMModel):
    period: str
    category_id: UUID
    planned_amount: int = 0
    note: str | None = None


class BudgetPlanUpdate(ORMModel):
    period: str | None = None
    category_id: UUID | None = None
    planned_amount: int | None = None
    note: str | None = None


class BudgetPlanRead(ORMModel):
    id: UUID
    period: str
    category_id: UUID
    planned_amount: int
    note: str | None = None
    created_at: datetime
    updated_at: datetime


class TransactionClassifyPayload(ORMModel):
    payment_type: str | None = None
    budget_category_id: UUID | None = None
    linked_activity_id: UUID | None = None
    match_status: str | None = None
    review_status: str | None = None
    review_note: str | None = None
