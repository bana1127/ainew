"""task38: budget management

Revision ID: 20260603_0014
Revises: 20260603_0013
Create Date: 2026-06-03
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260603_0014"
down_revision = "20260603_0013"
branch_labels = None
depends_on = None


DEFAULT_CATEGORIES = [
    ("회비", "income", 10),
    ("활동비", "income", 20),
    ("학교 지원금", "income", 30),
    ("기타 수입", "income", 90),
    ("재료비", "expense", 10),
    ("대관비", "expense", 20),
    ("식비", "expense", 30),
    ("홍보비", "expense", 40),
    ("비품비", "expense", 50),
    ("환불", "expense", 60),
    ("기타 지출", "expense", 90),
]


def upgrade() -> None:
    op.create_table(
        "budget_categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["parent_id"], ["budget_categories.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", "type", name="uq_budget_categories_name_type"),
    )
    op.create_table(
        "budget_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("period", sa.String(50), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("planned_amount", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["category_id"], ["budget_categories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("period", "category_id", name="uq_budget_plans_period_category"),
    )
    op.add_column(
        "bank_transactions",
        sa.Column("budget_category_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "bank_transactions",
        sa.Column("linked_activity_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "bank_transactions",
        sa.Column("review_status", sa.String(50), nullable=False, server_default="open"),
    )
    op.add_column(
        "bank_transactions",
        sa.Column("review_note", sa.String(500), nullable=True),
    )
    op.create_foreign_key(
        "fk_bank_transactions_budget_category",
        "bank_transactions",
        "budget_categories",
        ["budget_category_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_bank_transactions_linked_activity",
        "bank_transactions",
        "activity_reports",
        ["linked_activity_id"],
        ["id"],
        ondelete="SET NULL",
    )

    for name, category_type, sort_order in DEFAULT_CATEGORIES:
        op.execute(
            sa.text(
                "insert into budget_categories (name, type, sort_order, is_active) "
                "values (:name, :type, :sort_order, true) "
                "on conflict (name, type) do nothing"
            ).bindparams(name=name, type=category_type, sort_order=sort_order)
        )


def downgrade() -> None:
    op.drop_constraint("fk_bank_transactions_linked_activity", "bank_transactions", type_="foreignkey")
    op.drop_constraint("fk_bank_transactions_budget_category", "bank_transactions", type_="foreignkey")
    op.drop_column("bank_transactions", "review_note")
    op.drop_column("bank_transactions", "review_status")
    op.drop_column("bank_transactions", "linked_activity_id")
    op.drop_column("bank_transactions", "budget_category_id")
    op.drop_table("budget_plans")
    op.drop_table("budget_categories")
