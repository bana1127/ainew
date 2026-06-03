from datetime import datetime
from typing import Any
from uuid import UUID

from app.schemas.common import ORMModel


class UploadedFileBase(ORMModel):
    original_filename: str
    stored_path: str
    stored_filename: str | None = None
    mime_type: str | None = None
    file_ext: str | None = None
    size_bytes: int | None = None
    file_type: str | None = None
    file_category: str | None = None
    file_role: str | None = None
    is_submission_file: bool = False
    submission_month: str | None = None
    version: int = 1
    preview_status: str | None = None
    preview_metadata_json: dict[str, Any] | None = None
    related_entity_type: str | None = None
    related_entity_id: UUID | None = None
    activity_report_id: UUID | None = None
    deleted_at: datetime | None = None


class UploadedFileCreate(UploadedFileBase):
    pass


class UploadedFileUpdate(ORMModel):
    original_filename: str | None = None
    stored_path: str | None = None
    mime_type: str | None = None
    file_type: str | None = None
    file_category: str | None = None
    file_role: str | None = None
    is_submission_file: bool | None = None
    submission_month: str | None = None
    related_entity_type: str | None = None
    related_entity_id: UUID | None = None
    activity_report_id: UUID | None = None
    deleted_at: datetime | None = None
    preview_status: str | None = None
    preview_metadata_json: dict[str, Any] | None = None


class UploadedFileRead(UploadedFileBase):
    id: UUID
    created_at: datetime
    updated_at: datetime | None = None
    preview_available: bool = False
    download_url: str | None = None

    @classmethod
    def from_orm_with_extras(cls, obj: object) -> "UploadedFileRead":
        from app.schemas.common import ORMModel  # local to avoid circular
        data = {col: getattr(obj, col, None) for col in cls.model_fields}
        data["preview_available"] = _is_previewable(
            getattr(obj, "file_ext", None),
            getattr(obj, "mime_type", None),
        )
        file_id = getattr(obj, "id", None)
        data["download_url"] = f"/api/files/{file_id}/download" if file_id else None
        return cls.model_validate(data)


def _is_previewable(ext: str | None, mime: str | None) -> bool:
    if ext:
        ext = ext.lower().lstrip(".")
        if ext in {"pdf", "png", "jpg", "jpeg", "webp", "gif", "xlsx", "xls", "csv", "zip"}:
            return True
    if mime:
        if mime.startswith("image/") or mime == "application/pdf":
            return True
    return False
