"""File management router.

Provides:
  POST   /upload                  — upload file (legacy, kept for compatibility)
  GET    /                        — list files
  GET    /{file_id}               — file detail
  GET    /{file_id}/preview       — preview metadata JSON
  GET    /{file_id}/preview/inline — inline file content (PDF/image)
  GET    /{file_id}/download      — download with original filename
  DELETE /{file_id}               — soft delete
  PATCH  /{file_id}/activity      — link/unlink activity
  PATCH  /{file_id}/submission    — set submission flags
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models import UploadedFile
from app.routers.common import commit_or_400, get_or_404
from app.schemas import UploadedFileRead
from app.services.file_preview_service import build_file_preview
from app.services.file_storage_service import resolve_abs_path


router = APIRouter()


# ── helpers ───────────────────────────────────────────────────────────────────

def _file_to_dict(f: UploadedFile) -> dict[str, Any]:
    ext = f.file_ext or (Path(f.original_filename).suffix.lower().lstrip(".") or None)
    previewable = ext in {
        "pdf", "png", "jpg", "jpeg", "webp", "gif",
        "xlsx", "xls", "csv", "zip", "hwp", "hwpx",
    } if ext else False
    return {
        "id": str(f.id),
        "activity_report_id": str(f.activity_report_id) if f.activity_report_id else None,
        "original_filename": f.original_filename,
        "stored_filename": f.stored_filename,
        "mime_type": f.mime_type,
        "file_ext": ext,
        "size_bytes": f.size_bytes,
        "file_type": f.file_type,
        "file_category": f.file_category,
        "file_role": f.file_role,
        "is_submission_file": f.is_submission_file,
        "submission_month": f.submission_month,
        "version": f.version,
        "preview_status": f.preview_status,
        "preview_available": previewable,
        "preview_metadata": f.preview_metadata_json,
        "related_entity_type": f.related_entity_type,
        "related_entity_id": str(f.related_entity_id) if f.related_entity_id else None,
        "deleted_at": f.deleted_at.isoformat() if f.deleted_at else None,
        "created_at": f.created_at.isoformat() if f.created_at else None,
        "download_url": f"/api/files/{f.id}/download",
    }


def _get_active_or_404(db: Session, file_id: UUID) -> UploadedFile:
    f = db.get(UploadedFile, file_id)
    if not f:
        raise HTTPException(status_code=404, detail="File not found")
    return f


# ── legacy upload (kept for backward compatibility) ────────────────────────────

@router.post("/upload", response_model=UploadedFileRead)
def upload_file(
    file: UploadFile = File(...),
    file_type: str | None = Form(default=None),
    related_entity_type: str | None = Form(default=None),
    related_entity_id: UUID | None = Form(default=None),
    db: Session = Depends(get_db),
) -> UploadedFile:
    settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    suffix = Path(file.filename or "").suffix
    stored_name = f"{uuid4()}{suffix}"
    stored_path = settings.UPLOAD_DIR / stored_name

    with stored_path.open("wb") as output:
        while chunk := file.file.read(1024 * 1024):
            output.write(chunk)

    from app.services.file_classification_service import classify_uploaded_file
    classification = classify_uploaded_file(file.filename or "", file.content_type)

    record = UploadedFile(
        original_filename=file.filename or stored_name,
        stored_path=(Path("uploads") / stored_name).as_posix(),
        stored_filename=stored_name,
        mime_type=file.content_type,
        file_ext=Path(file.filename or "").suffix.lower().lstrip(".") or None,
        file_type=file_type or classification.file_category,
        file_category=classification.file_category,
        file_role=classification.file_role,
        related_entity_type=related_entity_type,
        related_entity_id=related_entity_id,
    )
    db.add(record)
    commit_or_400(db, "Could not save uploaded file metadata")
    db.refresh(record)
    return record


# ── list ──────────────────────────────────────────────────────────────────────

@router.get("")
def list_files(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    file_type: str | None = None,
    file_category: str | None = None,
    activity_report_id: UUID | None = None,
    include_deleted: bool = False,
    db: Session = Depends(get_db),
) -> list[dict]:
    stmt = select(UploadedFile)
    if file_type:
        stmt = stmt.where(UploadedFile.file_type == file_type)
    if file_category:
        stmt = stmt.where(UploadedFile.file_category == file_category)
    if activity_report_id:
        stmt = stmt.where(UploadedFile.activity_report_id == activity_report_id)
    if not include_deleted:
        stmt = stmt.where(UploadedFile.deleted_at.is_(None))
    return [_file_to_dict(f) for f in db.scalars(stmt.offset(skip).limit(limit))]


# ── detail ────────────────────────────────────────────────────────────────────

@router.get("/{file_id}")
def get_file(file_id: UUID, db: Session = Depends(get_db)) -> dict:
    return _file_to_dict(_get_active_or_404(db, file_id))


# ── preview metadata ──────────────────────────────────────────────────────────

@router.get("/{file_id}/preview")
def get_file_preview(file_id: UUID, db: Session = Depends(get_db)) -> dict:
    """Return preview metadata. Never raises a 500 — returns error info instead."""
    f = _get_active_or_404(db, file_id)
    abs_path = resolve_abs_path(f)
    preview = build_file_preview(
        file_id=str(file_id),
        abs_path=abs_path,
        ext=f.file_ext,
        mime_type=f.mime_type,
    )
    # Cache preview metadata
    if preview.get("type") not in ("error", "unsupported"):
        f.preview_metadata_json = preview
        f.preview_status = "ready"
        try:
            db.commit()
        except Exception:
            db.rollback()
    return preview


# ── inline content (PDF / image) ──────────────────────────────────────────────

@router.get("/{file_id}/preview/inline")
def get_file_inline(file_id: UUID, db: Session = Depends(get_db)) -> FileResponse:
    """Return the raw file for inline display (PDF / images)."""
    f = _get_active_or_404(db, file_id)
    abs_path = resolve_abs_path(f)
    if not abs_path.exists():
        raise HTTPException(status_code=404, detail="실제 파일을 찾을 수 없습니다.")
    media_type = f.mime_type or "application/octet-stream"
    return FileResponse(
        path=str(abs_path),
        media_type=media_type,
        headers={"Content-Disposition": "inline"},
    )


# ── download ──────────────────────────────────────────────────────────────────

@router.get("/{file_id}/download")
def download_file(file_id: UUID, db: Session = Depends(get_db)) -> FileResponse:
    """Download with original filename preserved.

    Uses RFC 5987 (filename*=UTF-8''...) to safely pass non-ASCII filenames
    (Korean, etc.) in the Content-Disposition header without encoding errors.
    """
    from urllib.parse import quote
    f = _get_active_or_404(db, file_id)
    abs_path = resolve_abs_path(f)
    if not abs_path.exists():
        raise HTTPException(status_code=404, detail="실제 파일을 찾을 수 없습니다.")
    # RFC 5987: percent-encode the filename in UTF-8
    encoded = quote(f.original_filename, safe="", encoding="utf-8")
    # Provide both ASCII fallback and UTF-8 encoded form
    ascii_fallback = f.original_filename.encode("ascii", errors="replace").decode("ascii").replace('"', '\\"')
    disposition = f'attachment; filename="{ascii_fallback}"; filename*=UTF-8\'\'{encoded}'
    return FileResponse(
        path=str(abs_path),
        media_type=f.mime_type or "application/octet-stream",
        headers={"Content-Disposition": disposition},
    )


# ── soft delete ───────────────────────────────────────────────────────────────

@router.delete("/{file_id}")
def delete_file(file_id: UUID, db: Session = Depends(get_db)) -> dict:
    """Soft delete — sets deleted_at. Actual file is retained on disk."""
    f = _get_active_or_404(db, file_id)
    f.deleted_at = datetime.now(tz=timezone.utc)
    commit_or_400(db, "Could not soft-delete file")
    return {"ok": True, "deleted_id": str(file_id)}


# ── link/unlink activity ──────────────────────────────────────────────────────

class ActivityPatchPayload(BaseModel):
    activity_id: UUID | None = None


@router.patch("/{file_id}/activity")
def patch_file_activity(
    file_id: UUID,
    payload: ActivityPatchPayload,
    db: Session = Depends(get_db),
) -> dict:
    f = _get_active_or_404(db, file_id)
    f.activity_report_id = payload.activity_id
    commit_or_400(db, "Could not update file activity link")
    return _file_to_dict(f)


# ── submission flags ──────────────────────────────────────────────────────────

class SubmissionPatchPayload(BaseModel):
    is_submission_file: bool | None = None
    submission_month: str | None = None
    file_category: str | None = None
    file_role: str | None = None


@router.patch("/{file_id}/submission")
def patch_file_submission(
    file_id: UUID,
    payload: SubmissionPatchPayload,
    db: Session = Depends(get_db),
) -> dict:
    f = _get_active_or_404(db, file_id)
    if payload.is_submission_file is not None:
        f.is_submission_file = payload.is_submission_file
    if payload.submission_month is not None:
        f.submission_month = payload.submission_month
    if payload.file_category is not None:
        f.file_category = payload.file_category
        f.file_type = payload.file_category
    if payload.file_role is not None:
        f.file_role = payload.file_role
    commit_or_400(db, "Could not update file submission flags")
    return _file_to_dict(f)
