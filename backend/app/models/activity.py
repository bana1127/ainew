from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import Date, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from typing import Any
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.member import Member
    from app.models.receipt import Receipt


class ActivityCategory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "activity_categories"

    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    required_fields_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    report_template: Mapped[str | None] = mapped_column(Text, nullable=True)

    reference_reports: Mapped[list[ReferenceReport]] = relationship(
        back_populates="category"
    )
    activity_reports: Mapped[list[ActivityReport]] = relationship(
        back_populates="category"
    )


class ReferenceReport(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "reference_reports"

    category_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("activity_categories.id"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)

    category: Mapped[ActivityCategory | None] = relationship(
        back_populates="reference_reports"
    )


class ActivityReport(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "activity_reports"

    category_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("activity_categories.id"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    activity_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    input_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    generated_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    final_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="draft", nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    category: Mapped[ActivityCategory | None] = relationship(
        back_populates="activity_reports"
    )
    participants: Mapped[list[ActivityParticipant]] = relationship(
        back_populates="activity_report",
        cascade="all, delete-orphan",
    )
    receipts: Mapped[list[Receipt]] = relationship(back_populates="activity_report")


class ActivityParticipant(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "activity_participants"
    __table_args__ = (
        UniqueConstraint(
            "activity_report_id",
            "member_id",
            name="uq_activity_participants_report_member",
        ),
    )

    activity_report_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("activity_reports.id"),
        nullable=False,
    )
    # nullable: external participants have no member_id
    member_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("members.id"),
        nullable=True,
    )
    role: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    raw_response_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    # external participant fields (used when member_id is None)
    external_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    external_affiliation: Mapped[str | None] = mapped_column(String(200), nullable=True)
    external_student_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    source_file_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("uploaded_files.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    activity_report: Mapped[ActivityReport] = relationship(back_populates="participants")
    member: Mapped[Member | None] = relationship(back_populates="activity_participants")
