from datetime import datetime
from uuid import UUID

from app.schemas.common import ORMModel


class UploadedFileBase(ORMModel):
    original_filename: str
    stored_path: str
    mime_type: str | None = None
    file_type: str | None = None
    related_entity_type: str | None = None
    related_entity_id: UUID | None = None


class UploadedFileCreate(UploadedFileBase):
    pass


class UploadedFileUpdate(ORMModel):
    original_filename: str | None = None
    stored_path: str | None = None
    mime_type: str | None = None
    file_type: str | None = None
    related_entity_type: str | None = None
    related_entity_id: UUID | None = None


class UploadedFileRead(UploadedFileBase):
    id: UUID
    created_at: datetime

