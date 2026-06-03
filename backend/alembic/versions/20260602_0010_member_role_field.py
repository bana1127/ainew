"""task26-booster: add role field to members table

Revision ID: 20260602_0010
Revises: 20260602_0009
Create Date: 2026-06-02 00:00:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260602_0010"
down_revision: Union[str, None] = "20260602_0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("members", sa.Column("role", sa.String(100), nullable=True))


def downgrade() -> None:
    op.drop_column("members", "role")
