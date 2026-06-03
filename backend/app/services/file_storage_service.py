"""File storage service.

Handles saving uploaded files to disk and creating UploadedFile DB records.
Files are organized under:
  uploads/
    activities/{activity_id[:8]}/    ← activity-scoped files
    general/                          ← non-activity files
"""
from __future__ import annotations

import mimetypes
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.file import UploadedFile
from app.routers.common import commit_or_400
from app.services.file_classification_service import classify_uploaded_file


def save_activity_file(
    file: UploadFile,
    db: Session,
    activity_report_id: UUID | None = None,
    file_category: str | None = None,
    file_role: str | None = None,
    is_submission_file: bool = False,
    submission_month: str | None = None,
) -> UploadedFile:
    """Save a file and create a DB record linked to an activity."""
    original_name = file.filename or "unnamed"
    ext = Path(original_name).suffix.lower()
    stored_name = f"{uuid4()}{ext}"

    # Build storage path
    if activity_report_id:
        subdir = settings.UPLOAD_DIR / "activities" / str(activity_report_id)[:8]
    else:
        subdir = settings.UPLOAD_DIR / "general"

    subdir.mkdir(parents=True, exist_ok=True)
    abs_path = subdir / stored_name

    with abs_path.open("wb") as out:
        while chunk := file.file.read(1024 * 1024):
            out.write(chunk)

    size_bytes = abs_path.stat().st_size

    # Relative stored_path
    try:
        rel_path = abs_path.relative_to(settings.UPLOAD_DIR.parent)
    except ValueError:
        rel_path = Path("uploads") / stored_name
    stored_path_str = rel_path.as_posix()

    # Determine mime type
    mime = file.content_type or mimetypes.guess_type(original_name)[0]

    # Auto-classify if not provided
    ext_no_dot = ext.lstrip(".") if ext else ""
    if not file_category:
        classification = classify_uploaded_file(original_name, mime)
        file_category = classification.file_category
        if not file_role:
            file_role = classification.file_role

    record = UploadedFile(
        original_filename=original_name,
        stored_path=stored_path_str,
        stored_filename=stored_name,
        mime_type=mime,
        file_ext=ext_no_dot if ext_no_dot else None,
        size_bytes=size_bytes,
        file_type=file_category,
        file_category=file_category,
        file_role=file_role,
        is_submission_file=is_submission_file,
        submission_month=submission_month,
        activity_report_id=activity_report_id,
        preview_status="pending",
    )
    db.add(record)
    commit_or_400(db, "Could not save file metadata")
    db.refresh(record)
    return record


def save_bytes_to_vault(
    db: Session,
    file_bytes: bytes,
    original_filename: str,
    activity_report_id: UUID | None = None,
    file_category: str | None = None,
    file_role: str | None = None,
) -> UploadedFile:
    """Save raw bytes to the file vault and create a DB record."""
    import mimetypes as _mt
    ext = Path(original_filename).suffix.lower()
    stored_name = f"{uuid4()}{ext}"

    if activity_report_id:
        subdir = settings.UPLOAD_DIR / "activities" / str(activity_report_id)[:8]
    else:
        subdir = settings.UPLOAD_DIR / "general"

    subdir.mkdir(parents=True, exist_ok=True)
    abs_path = subdir / stored_name
    abs_path.write_bytes(file_bytes)
    size_bytes = len(file_bytes)

    try:
        rel_path = abs_path.relative_to(settings.UPLOAD_DIR.parent)
    except ValueError:
        rel_path = Path("uploads") / stored_name
    stored_path_str = rel_path.as_posix()

    mime = _mt.guess_type(original_filename)[0] or "application/octet-stream"
    ext_no_dot = ext.lstrip(".") if ext else None

    record = UploadedFile(
        original_filename=original_filename,
        stored_path=stored_path_str,
        stored_filename=stored_name,
        mime_type=mime,
        file_ext=ext_no_dot,
        size_bytes=size_bytes,
        file_type=file_category or "other",
        file_category=file_category or "other",
        file_role=file_role or "source",
        activity_report_id=activity_report_id,
        preview_status="pending",
    )
    db.add(record)
    commit_or_400(db, "Could not save file metadata")
    db.refresh(record)
    return record


def resolve_abs_path(record: UploadedFile) -> Path:
    """Return the absolute path to the stored file."""
    stored = Path(record.stored_path)
    if stored.is_absolute():
        return stored
    # stored_path is relative to settings.UPLOAD_DIR.parent (project backend dir)
    candidate = settings.UPLOAD_DIR.parent / stored
    if candidate.exists():
        return candidate
    # Fallback: relative to UPLOAD_DIR
    return settings.UPLOAD_DIR / stored.name
