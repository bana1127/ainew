"""membership fee policy metadata fields

Revision ID: 20260603_0012
Revises: 20260603_0011
Create Date: 2026-06-03
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260603_0012"
down_revision = "20260603_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("members", sa.Column("term_code", sa.String(50), nullable=True))
    op.add_column("payment_records", sa.Column("fee_tier", sa.String(50), nullable=True))
    op.add_column("payment_records", sa.Column("fee_rule_reason", sa.Text(), nullable=True))
    op.add_column("payment_records", sa.Column("joined_term", sa.String(50), nullable=True))
    op.add_column("payment_records", sa.Column("current_term", sa.String(50), nullable=True))


def downgrade() -> None:
    op.drop_column("payment_records", "current_term")
    op.drop_column("payment_records", "joined_term")
    op.drop_column("payment_records", "fee_rule_reason")
    op.drop_column("payment_records", "fee_tier")
    op.drop_column("members", "term_code")
