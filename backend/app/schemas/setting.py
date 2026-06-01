from datetime import datetime
from uuid import UUID

from app.schemas.common import JsonValue, ORMModel


class AppSettingBase(ORMModel):
    key: str
    value: JsonValue = None
    description: str | None = None


class AppSettingCreate(AppSettingBase):
    pass


class AppSettingUpdate(ORMModel):
    key: str | None = None
    value: JsonValue = None
    description: str | None = None


class AppSettingRead(AppSettingBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

