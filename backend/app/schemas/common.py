from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


JsonValue = dict[str, Any] | list[Any] | str | int | float | bool | None


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class UUIDReadMixin(ORMModel):
    id: UUID


class TimestampReadMixin(ORMModel):
    created_at: datetime
    updated_at: datetime

