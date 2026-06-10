"""task44: notification rules, delivery logs, n8n settings

Revision ID: 20260606_0018
Revises: 20260604_0017
Create Date: 2026-06-06
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260606_0018"
down_revision = "20260604_0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notification_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("reminder_type", sa.String(100), nullable=False),
        sa.Column("target_scope", sa.String(50), nullable=False, server_default="global"),
        sa.Column("channel", sa.String(50), nullable=False, server_default="gmail"),
        sa.Column("send_time", sa.Time(), nullable=True),
        sa.Column("days_before", sa.Integer(), nullable=True),
        sa.Column("days_after", sa.Integer(), nullable=True),
        sa.Column("repeat_interval_days", sa.Integer(), nullable=True),
        sa.Column("max_send_count", sa.Integer(), nullable=True),
        sa.Column(
            "require_confirm_before_send",
            sa.Boolean(),
            nullable=False,
            server_default="true",
        ),
        sa.Column("term", sa.String(50), nullable=True),
        sa.Column("quarter", sa.String(50), nullable=True),
        sa.Column("activity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("conditions", postgresql.JSONB(), nullable=True),
        sa.Column("template_subject", sa.String(255), nullable=False),
        sa.Column("template_body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["activity_id"], ["activity_reports.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notification_rules_enabled", "notification_rules", ["enabled"])
    op.create_index("ix_notification_rules_reminder_type", "notification_rules", ["reminder_type"])

    op.create_table(
        "notification_delivery_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rule_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reminder_type", sa.String(100), nullable=False),
        sa.Column("target_type", sa.String(100), nullable=False),
        sa.Column("target_id", sa.String(100), nullable=False),
        sa.Column("recipient_email", sa.String(255), nullable=False),
        sa.Column("recipient_name", sa.String(150), nullable=True),
        sa.Column("subject", sa.String(255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("target_url", sa.String(500), nullable=True),
        sa.Column("provider", sa.String(50), nullable=False, server_default="n8n"),
        sa.Column("provider_message_id", sa.String(255), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["rule_id"], ["notification_rules.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notification_delivery_logs_rule", "notification_delivery_logs", ["rule_id"])
    op.create_index(
        "ix_notification_delivery_logs_dedupe",
        "notification_delivery_logs",
        ["rule_id", "target_type", "target_id", "recipient_email", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_notification_delivery_logs_dedupe", table_name="notification_delivery_logs")
    op.drop_index("ix_notification_delivery_logs_rule", table_name="notification_delivery_logs")
    op.drop_table("notification_delivery_logs")
    op.drop_index("ix_notification_rules_reminder_type", table_name="notification_rules")
    op.drop_index("ix_notification_rules_enabled", table_name="notification_rules")
    op.drop_table("notification_rules")
