from __future__ import annotations

from datetime import datetime, time
from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, Time, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Notification(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "notifications"

    type: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(50), default="info", nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    related_entity_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    related_entity_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class NotificationRule(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "notification_rules"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    reminder_type: Mapped[str] = mapped_column(String(100), nullable=False)
    target_scope: Mapped[str] = mapped_column(String(50), default="global", nullable=False)
    channel: Mapped[str] = mapped_column(String(50), default="gmail", nullable=False)
    send_time: Mapped[time | None] = mapped_column(Time(), nullable=True)
    days_before: Mapped[int | None] = mapped_column(Integer, nullable=True)
    days_after: Mapped[int | None] = mapped_column(Integer, nullable=True)
    repeat_interval_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_send_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    require_confirm_before_send: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    term: Mapped[str | None] = mapped_column(String(50), nullable=True)
    quarter: Mapped[str | None] = mapped_column(String(50), nullable=True)
    activity_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("activity_reports.id", ondelete="SET NULL"),
        nullable=True,
    )
    conditions: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    template_subject: Mapped[str] = mapped_column(String(255), nullable=False)
    template_body: Mapped[str] = mapped_column(Text, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    delivery_logs: Mapped[list["NotificationDeliveryLog"]] = relationship(
        back_populates="rule",
        cascade="all, delete-orphan",
    )


class NotificationDeliveryLog(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "notification_delivery_logs"

    rule_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("notification_rules.id", ondelete="SET NULL"),
        nullable=True,
    )
    reminder_type: Mapped[str] = mapped_column(String(100), nullable=False)
    target_type: Mapped[str] = mapped_column(String(100), nullable=False)
    target_id: Mapped[str] = mapped_column(String(100), nullable=False)
    recipient_email: Mapped[str] = mapped_column(String(255), nullable=False)
    recipient_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    target_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    provider: Mapped[str] = mapped_column(String(50), default="n8n", nullable=False)
    provider_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    rule: Mapped[NotificationRule | None] = relationship(back_populates="delivery_logs")
