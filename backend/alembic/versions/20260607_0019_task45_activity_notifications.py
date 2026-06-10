"""task45: activity notification defaults and activity photo evidence

Revision ID: 20260607_0019
Revises: 20260606_0018
Create Date: 2026-06-07
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260607_0019"
down_revision = "20260606_0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "receipts",
        "amount",
        existing_type=sa.Integer(),
        nullable=True,
    )


def downgrade() -> None:
    op.execute("UPDATE receipts SET amount = 0 WHERE amount IS NULL")
    op.alter_column(
        "receipts",
        "amount",
        existing_type=sa.Integer(),
        nullable=False,
    )
