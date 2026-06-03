"""task27: make activity_participants.member_id nullable, add external participant fields

Revision ID: 20260603_0011
Revises: 20260602_0010
Create Date: 2026-06-03
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

revision = "20260603_0011"
down_revision = "20260602_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Make member_id nullable (for external participants)
    op.alter_column(
        "activity_participants",
        "member_id",
        existing_type=PG_UUID(as_uuid=True),
        nullable=True,
    )

    # 2. Add external participant fields
    op.add_column(
        "activity_participants",
        sa.Column("external_name", sa.String(150), nullable=True),
    )
    op.add_column(
        "activity_participants",
        sa.Column("external_affiliation", sa.String(200), nullable=True),
    )
    op.add_column(
        "activity_participants",
        sa.Column("external_student_id", sa.String(50), nullable=True),
    )

    # 3. Add source_file_id (FK to uploaded_files, nullable)
    op.add_column(
        "activity_participants",
        sa.Column(
            "source_file_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("uploaded_files.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("activity_participants", "source_file_id")
    op.drop_column("activity_participants", "external_student_id")
    op.drop_column("activity_participants", "external_affiliation")
    op.drop_column("activity_participants", "external_name")
    op.alter_column(
        "activity_participants",
        "member_id",
        existing_type=PG_UUID(as_uuid=True),
        nullable=False,
    )
