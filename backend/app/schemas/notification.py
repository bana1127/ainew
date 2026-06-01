from datetime import datetime
from uuid import UUID

from app.schemas.common import ORMModel


class NotificationBase(ORMModel):
    type: str
    title: str
    message: str
    severity: str = "info"
    is_read: bool = False
    related_entity_type: str | None = None
    related_entity_id: UUID | None = None


class NotificationCreate(NotificationBase):
    pass


class NotificationUpdate(ORMModel):
    type: str | None = None
    title: str | None = None
    message: str | None = None
    severity: str | None = None
    is_read: bool | None = None
    related_entity_type: str | None = None
    related_entity_id: UUID | None = None


class NotificationRead(NotificationBase):
    id: UUID
    created_at: datetime

