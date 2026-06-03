"""task26-booster: add member roster fields (gender, grade, birth_year, joined_term, is_executive)

Revision ID: 20260602_0009
Revises: 20260602_0008
Create Date: 2026-06-02 00:00:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260602_0009"
down_revision: Union[str, None] = "20260602_0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("members", sa.Column("gender", sa.String(20), nullable=True))
    op.add_column("members", sa.Column("grade", sa.String(20), nullable=True))
    op.add_column("members", sa.Column("birth_year", sa.Integer(), nullable=True))
    op.add_column("members", sa.Column("joined_term", sa.String(50), nullable=True))
    op.add_column("members", sa.Column("is_executive", sa.Boolean(), server_default="false", nullable=False))


def downgrade() -> None:
    op.drop_column("members", "is_executive")
    op.drop_column("members", "joined_term")
    op.drop_column("members", "birth_year")
    op.drop_column("members", "grade")
    op.drop_column("members", "gender")
