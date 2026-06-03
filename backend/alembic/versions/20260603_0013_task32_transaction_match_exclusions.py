"""task32: transaction_match_exclusions table

Revision ID: 20260603_0013
Revises: 20260603_0012
Create Date: 2026-06-03
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260603_0013"
down_revision = "20260603_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "transaction_match_exclusions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("transaction_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("activity_report_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("payment_type", sa.String(100), nullable=False, server_default="activity_fee"),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["transaction_id"], ["bank_transactions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["activity_report_id"], ["activity_reports.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "transaction_id", "activity_report_id", "payment_type",
            name="uq_tx_exclusion_tx_activity_type",
        ),
    )
    op.create_index(
        "ix_tx_exclusion_activity_type_active",
        "transaction_match_exclusions",
        ["activity_report_id", "payment_type", "is_active"],
    )


def downgrade() -> None:
    op.drop_index("ix_tx_exclusion_activity_type_active", table_name="transaction_match_exclusions")
    op.drop_table("transaction_match_exclusions")
