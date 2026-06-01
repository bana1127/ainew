"""add activity_report_id to payment_records

Revision ID: 20260601_0002
Revises: 20260531_0001
Create Date: 2026-06-01 00:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260601_0002"
down_revision: Union[str, None] = "20260531_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "payment_records",
        sa.Column(
            "activity_report_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("activity_reports.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_payment_records_activity_report_id",
        "payment_records",
        ["activity_report_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_payment_records_activity_report_id", table_name="payment_records")
    op.drop_column("payment_records", "activity_report_id")
