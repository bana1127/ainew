"""task43: quarterly finance, evidence document types, budget exclusion, manual match

Revision ID: 20260604_0017
Revises: 20260604_0016
Create Date: 2026-06-04
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260604_0017"
down_revision = "20260604_0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── BankTransaction: budget exclusion fields ──────────────────────────────
    op.add_column(
        "bank_transactions",
        sa.Column("exclude_from_budget", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "bank_transactions",
        sa.Column("exclude_from_income", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "bank_transactions",
        sa.Column("exclude_from_expense", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "bank_transactions",
        sa.Column("exclude_reason", sa.Text(), nullable=True),
    )
    op.add_column(
        "bank_transactions",
        sa.Column("excluded_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── Receipts: document type + parsed_data + manual_data ───────────────────
    op.add_column(
        "receipts",
        sa.Column("document_type", sa.String(50), nullable=False, server_default="unknown"),
    )
    op.add_column(
        "receipts",
        sa.Column("title", sa.String(255), nullable=True),
    )
    op.add_column(
        "receipts",
        sa.Column("parsed_data", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "receipts",
        sa.Column("manual_data", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "receipts",
        sa.Column(
            "transaction_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("bank_transactions.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    # index for quarter-based transaction queries
    op.create_index(
        "ix_bank_transactions_exclude_from_budget",
        "bank_transactions",
        ["exclude_from_budget"],
    )
    op.create_index(
        "ix_receipts_document_type",
        "receipts",
        ["document_type"],
    )


def downgrade() -> None:
    op.drop_index("ix_receipts_document_type", table_name="receipts")
    op.drop_index("ix_bank_transactions_exclude_from_budget", table_name="bank_transactions")

    op.drop_column("receipts", "transaction_id")
    op.drop_column("receipts", "manual_data")
    op.drop_column("receipts", "parsed_data")
    op.drop_column("receipts", "title")
    op.drop_column("receipts", "document_type")

    op.drop_column("bank_transactions", "excluded_at")
    op.drop_column("bank_transactions", "exclude_reason")
    op.drop_column("bank_transactions", "exclude_from_expense")
    op.drop_column("bank_transactions", "exclude_from_income")
    op.drop_column("bank_transactions", "exclude_from_budget")
