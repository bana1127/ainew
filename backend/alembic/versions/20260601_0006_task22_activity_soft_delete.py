"""task22: add soft delete timestamp to activity_reports

Revision ID: 20260601_0006
Revises: 20260601_0005
Create Date: 2026-06-01 23:40:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260601_0006"
down_revision: Union[str, None] = "20260601_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("activity_reports", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_activity_reports_deleted_at", "activity_reports", ["deleted_at"])


def downgrade() -> None:
    op.drop_index("ix_activity_reports_deleted_at", table_name="activity_reports")
    op.drop_column("activity_reports", "deleted_at")
