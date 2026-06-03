"""task21: add refund fields to payment_records and create payment_adjustment_logs

Revision ID: 20260601_0005
Revises: 20260601_0004
Create Date: 2026-06-01 14:00:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260601_0005"
down_revision: Union[str, None] = "20260601_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add refund fields to payment_records
    op.add_column(
        "payment_records",
        sa.Column("refund_status", sa.String(50), nullable=True, server_default="none"),
    )
    op.add_column("payment_records", sa.Column("refund_amount", sa.Integer(), nullable=True))
    op.add_column(
        "payment_records",
        sa.Column(
            "refund_transaction_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("bank_transactions.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column("payment_records", sa.Column("refund_reason", sa.Text(), nullable=True))
    op.add_column(
        "payment_records",
        sa.Column("refunded_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index("ix_payment_records_refund_status", "payment_records", ["refund_status"])

    # 2. Create payment_adjustment_logs table
    op.create_table(
        "payment_adjustment_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "payment_record_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("payment_records.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "transaction_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("bank_transactions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("previous_status", sa.String(50), nullable=True),
        sa.Column("new_status", sa.String(50), nullable=True),
        sa.Column("previous_paid_amount", sa.Integer(), nullable=True),
        sa.Column("new_paid_amount", sa.Integer(), nullable=True),
        sa.Column("refund_amount", sa.Integer(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_payment_adjustment_logs_payment_record_id",
        "payment_adjustment_logs",
        ["payment_record_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_payment_adjustment_logs_payment_record_id",
        table_name="payment_adjustment_logs",
    )
    op.drop_table("payment_adjustment_logs")
    op.drop_index("ix_payment_records_refund_status", table_name="payment_records")
    for col in ["refunded_at", "refund_reason", "refund_transaction_id", "refund_amount", "refund_status"]:
        op.drop_column("payment_records", col)
