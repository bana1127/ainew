"""task18: add participant status, raw_response_json, activity_feedbacks table

Revision ID: 20260601_0003
Revises: 20260601_0002
Create Date: 2026-06-01 12:00:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260601_0003"
down_revision: Union[str, None] = "20260601_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add status and raw_response_json to activity_participants
    op.add_column(
        "activity_participants",
        sa.Column("status", sa.String(50), nullable=True),
    )
    op.add_column(
        "activity_participants",
        sa.Column("raw_response_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )

    # 2. Create activity_feedbacks table
    op.create_table(
        "activity_feedbacks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "activity_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("activity_reports.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "member_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("members.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("response_type", sa.String(100), nullable=False, default="activity_feedback_form"),
        sa.Column("summary_text", sa.Text(), nullable=True),
        sa.Column("raw_response_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_activity_feedbacks_activity_id", "activity_feedbacks", ["activity_id"])
    op.create_index("ix_activity_feedbacks_member_id", "activity_feedbacks", ["member_id"])


def downgrade() -> None:
    op.drop_index("ix_activity_feedbacks_member_id", table_name="activity_feedbacks")
    op.drop_index("ix_activity_feedbacks_activity_id", table_name="activity_feedbacks")
    op.drop_table("activity_feedbacks")
    op.drop_column("activity_participants", "raw_response_json")
    op.drop_column("activity_participants", "status")
