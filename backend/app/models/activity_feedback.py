from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ActivityFeedback(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "activity_feedbacks"

    activity_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("activity_reports.id", ondelete="CASCADE"),
        nullable=False,
    )
    member_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("members.id", ondelete="SET NULL"),
        nullable=True,
    )
    response_type: Mapped[str] = mapped_column(
        String(100),
        default="activity_feedback_form",
        nullable=False,
    )
    summary_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_response_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
