"""task: membership fee manual source fields

Revision ID: 20260603_0015
Revises: 20260603_0014
Create Date: 2026-06-03
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260603_0015"
down_revision = "20260603_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("payment_records", sa.Column("payment_source", sa.String(50), nullable=True))
    op.add_column("payment_records", sa.Column("manual_note", sa.Text(), nullable=True))
    op.execute(
        "update payment_records "
        "set payment_source = 'transaction_match' "
        "where transaction_id is not null and payment_source is null"
    )


def downgrade() -> None:
    op.drop_column("payment_records", "manual_note")
    op.drop_column("payment_records", "payment_source")
