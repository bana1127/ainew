"""create initial clubagent tables

Revision ID: 20260531_0001
Revises:
Create Date: 2026-05-31 00:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260531_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def uuid_column() -> sa.Column:
    return sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False)


def timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "members",
        uuid_column(),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("student_id", sa.String(length=50), nullable=True),
        sa.Column("department", sa.String(length=100), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("memo", sa.Text(), nullable=True),
        *timestamps(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_members_name", "members", ["name"])
    op.create_index("ix_members_status", "members", ["status"])
    op.create_index("ix_members_student_id", "members", ["student_id"])

    op.create_table(
        "activity_categories",
        uuid_column(),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("required_fields_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("report_template", sa.Text(), nullable=True),
        *timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    op.create_table(
        "uploaded_files",
        uuid_column(),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("stored_path", sa.String(length=500), nullable=False),
        sa.Column("mime_type", sa.String(length=150), nullable=True),
        sa.Column("file_type", sa.String(length=100), nullable=True),
        sa.Column("related_entity_type", sa.String(length=100), nullable=True),
        sa.Column("related_entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "notifications",
        uuid_column(),
        sa.Column("type", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(length=50), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False),
        sa.Column("related_entity_type", sa.String(length=100), nullable=True),
        sa.Column("related_entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "app_settings",
        uuid_column(),
        sa.Column("key", sa.String(length=150), nullable=False),
        sa.Column("value", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        *timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
    )

    op.create_table(
        "reference_reports",
        uuid_column(),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        *timestamps(),
        sa.ForeignKeyConstraint(["category_id"], ["activity_categories.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "activity_reports",
        uuid_column(),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("activity_date", sa.Date(), nullable=True),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("input_text", sa.Text(), nullable=True),
        sa.Column("generated_content", sa.Text(), nullable=True),
        sa.Column("final_content", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(["category_id"], ["activity_categories.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "bank_transactions",
        uuid_column(),
        sa.Column("transaction_datetime", sa.DateTime(timezone=True), nullable=True),
        sa.Column("transaction_type", sa.String(length=100), nullable=True),
        sa.Column("memo", sa.String(length=255), nullable=True),
        sa.Column("withdraw_amount", sa.Integer(), nullable=False),
        sa.Column("deposit_amount", sa.Integer(), nullable=False),
        sa.Column("balance", sa.Integer(), nullable=True),
        sa.Column("branch", sa.String(length=150), nullable=True),
        sa.Column("raw_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("matched_member_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("payment_type", sa.String(length=100), nullable=True),
        sa.Column("match_status", sa.String(length=50), nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(["matched_member_id"], ["members.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "activity_participants",
        uuid_column(),
        sa.Column("activity_report_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("member_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["activity_report_id"], ["activity_reports.id"]),
        sa.ForeignKeyConstraint(["member_id"], ["members.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "activity_report_id",
            "member_id",
            name="uq_activity_participants_report_member",
        ),
    )

    op.create_table(
        "receipts",
        uuid_column(),
        sa.Column("activity_report_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("file_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("receipt_date", sa.Date(), nullable=True),
        sa.Column("store_name", sa.String(length=255), nullable=True),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("payment_method", sa.String(length=100), nullable=True),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("evidence_status", sa.String(length=50), nullable=False),
        sa.Column("need_check", sa.Boolean(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        *timestamps(),
        sa.ForeignKeyConstraint(["activity_report_id"], ["activity_reports.id"]),
        sa.ForeignKeyConstraint(["file_id"], ["uploaded_files.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "payment_records",
        uuid_column(),
        sa.Column("member_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("period", sa.String(length=50), nullable=False),
        sa.Column("payment_type", sa.String(length=100), nullable=False),
        sa.Column("required_amount", sa.Integer(), nullable=False),
        sa.Column("paid_amount", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("transaction_id", postgresql.UUID(as_uuid=True), nullable=True),
        *timestamps(),
        sa.ForeignKeyConstraint(["member_id"], ["members.id"]),
        sa.ForeignKeyConstraint(["transaction_id"], ["bank_transactions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "member_id",
            "period",
            "payment_type",
            name="uq_payment_records_member_period_type",
        ),
    )


def downgrade() -> None:
    op.drop_table("payment_records")
    op.drop_table("receipts")
    op.drop_table("activity_participants")
    op.drop_table("bank_transactions")
    op.drop_table("activity_reports")
    op.drop_table("reference_reports")
    op.drop_table("app_settings")
    op.drop_table("notifications")
    op.drop_table("uploaded_files")
    op.drop_table("activity_categories")
    op.drop_index("ix_members_student_id", table_name="members")
    op.drop_index("ix_members_status", table_name="members")
    op.drop_index("ix_members_name", table_name="members")
    op.drop_table("members")

