"""task19: add file vault fields to uploaded_files

Revision ID: 20260601_0004
Revises: 20260601_0003
Create Date: 2026-06-01 13:00:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260601_0004"
down_revision: Union[str, None] = "20260601_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "uploaded_files",
        sa.Column(
            "activity_report_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("activity_reports.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column("uploaded_files", sa.Column("stored_filename", sa.String(255), nullable=True))
    op.add_column("uploaded_files", sa.Column("file_ext", sa.String(20), nullable=True))
    op.add_column("uploaded_files", sa.Column("size_bytes", sa.BigInteger(), nullable=True))
    op.add_column("uploaded_files", sa.Column("file_category", sa.String(50), nullable=True))
    op.add_column("uploaded_files", sa.Column("file_role", sa.String(50), nullable=True))
    op.add_column(
        "uploaded_files",
        sa.Column("is_submission_file", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.add_column("uploaded_files", sa.Column("submission_month", sa.String(10), nullable=True))
    op.add_column(
        "uploaded_files",
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
    )
    op.add_column("uploaded_files", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "uploaded_files",
        sa.Column("preview_status", sa.String(50), server_default=sa.text("'pending'"), nullable=True),
    )
    op.add_column(
        "uploaded_files",
        sa.Column(
            "preview_metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.add_column(
        "uploaded_files",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
    )

    op.create_index("ix_uploaded_files_activity_report_id", "uploaded_files", ["activity_report_id"])
    op.create_index("ix_uploaded_files_file_category", "uploaded_files", ["file_category"])
    op.create_index("ix_uploaded_files_deleted_at", "uploaded_files", ["deleted_at"])


def downgrade() -> None:
    op.drop_index("ix_uploaded_files_deleted_at", table_name="uploaded_files")
    op.drop_index("ix_uploaded_files_file_category", table_name="uploaded_files")
    op.drop_index("ix_uploaded_files_activity_report_id", table_name="uploaded_files")

    for col in [
        "updated_at", "preview_metadata_json", "preview_status",
        "deleted_at", "version", "submission_month", "is_submission_file",
        "file_role", "file_category", "size_bytes", "file_ext",
        "stored_filename", "activity_report_id",
    ]:
        op.drop_column("uploaded_files", col)
