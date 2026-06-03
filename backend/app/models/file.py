from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKeyMixin


class UploadedFile(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "uploaded_files"

    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_path: Mapped[str] = mapped_column(String(500), nullable=False)
    stored_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(150), nullable=True)
    file_ext: Mapped[str | None] = mapped_column(String(20), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    file_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    file_category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    file_role: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_submission_file: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    submission_month: Mapped[str | None] = mapped_column(String(10), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    preview_status: Mapped[str | None] = mapped_column(String(50), default="pending", nullable=True)
    preview_metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    related_entity_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    related_entity_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    activity_report_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=True,
    )

    receipts = relationship("Receipt", back_populates="file")
