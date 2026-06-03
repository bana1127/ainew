"""task25: add assistant action proposals

Revision ID: 20260602_0008
Revises: 20260602_0007
Create Date: 2026-06-02 00:00:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260602_0008"
down_revision: Union[str, None] = "20260602_0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "assistant_action_proposals",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action_type", sa.String(length=100), nullable=False),
        sa.Column("source", sa.String(length=100), nullable=False, server_default="assistant"),
        sa.Column("activity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("preview_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="pending"),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("risk_level", sa.String(length=50), nullable=False, server_default="medium"),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["activity_id"], ["activity_reports.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_assistant_action_proposals_status", "assistant_action_proposals", ["status"])
    op.create_index("ix_assistant_action_proposals_activity_id", "assistant_action_proposals", ["activity_id"])


def downgrade() -> None:
    op.drop_index("ix_assistant_action_proposals_activity_id", table_name="assistant_action_proposals")
    op.drop_index("ix_assistant_action_proposals_status", table_name="assistant_action_proposals")
    op.drop_table("assistant_action_proposals")
