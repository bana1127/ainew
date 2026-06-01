from __future__ import annotations

from typing import Any

from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AppSetting(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    value: Mapped[dict[str, Any] | list[Any] | str | int | float | bool | None] = (
        mapped_column(JSONB, nullable=True)
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

