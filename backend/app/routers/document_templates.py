"""Document template router.

Templates are stored as UploadedFile records with:
  file_category = "document_template"
  file_type     = template_type  (e.g. "activity_report")
  preview_metadata_json = {
    "template_name": ...,
    "description": ...,
    "template_type": ...,
    "is_default": false,
    "placeholder_fields": [...]
  }

API:
  POST /api/document-templates           — upload template
  GET  /api/document-templates           — list templates
  GET  /api/document-templates/{id}      — template detail
  GET  /api/document-templates/{id}/fields — placeholder list
"""
from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.file import UploadedFile
from app.routers.common import commit_or_400
from app.services.hwpx_template_service import extract_hwpx_placeholders


router = APIRouter()

TEMPLATE_CATEGORY = "document_template"


def _template_to_dict(f: UploadedFile) -> dict:
    meta = f.preview_metadata_json or {}
    return {
        "id": str(f.id),
        "name": meta.get("template_name") or f.original_filename,
        "description": meta.get("description") or "",
        "template_type": meta.get("template_type") or f.file_type or "other",
        "is_default": meta.get("is_default", False),
        "placeholder_fields": meta.get("placeholder_fields") or [],
        "original_filename": f.original_filename,
        "file_ext": f.file_ext,
        "size_bytes": f.size_bytes,
        "created_at": f.created_at.isoformat() if f.created_at else None,
        "download_url": f"/api/files/{f.id}/download",
    }


@router.post("")
def upload_template(
    file: UploadFile = File(...),
    name: str | None = Form(default=None),
    description: str | None = Form(default=None),
    template_type: str = Form(default="activity_report"),
    is_default: bool = Form(default=False),
    db: Session = Depends(get_db),
) -> dict:
    original_name = file.filename or "template.hwpx"
    ext = Path(original_name).suffix.lower()

    if ext not in {".hwpx", ".hwp"}:
        raise HTTPException(
            status_code=400,
            detail="템플릿 파일은 .hwpx 또는 .hwp 파일만 허용됩니다.",
        )

    # Save file
    stored_name = f"{uuid4()}{ext}"
    subdir = settings.UPLOAD_DIR / "templates"
    subdir.mkdir(parents=True, exist_ok=True)
    abs_path = subdir / stored_name

    with abs_path.open("wb") as out:
        while chunk := file.file.read(1024 * 1024):
            out.write(chunk)

    size_bytes = abs_path.stat().st_size

    try:
        rel_path = abs_path.relative_to(settings.UPLOAD_DIR.parent)
    except ValueError:
        rel_path = Path("uploads") / "templates" / stored_name

    # Extract placeholders (HWPX only)
    placeholder_fields: list[str] = []
    if ext == ".hwpx":
        try:
            placeholder_fields = extract_hwpx_placeholders(abs_path)
        except Exception:
            placeholder_fields = []

    template_name = name or original_name
    meta = {
        "template_name": template_name,
        "description": description or "",
        "template_type": template_type,
        "is_default": is_default,
        "placeholder_fields": placeholder_fields,
    }

    record = UploadedFile(
        original_filename=original_name,
        stored_path=rel_path.as_posix(),
        stored_filename=stored_name,
        mime_type=file.content_type or "application/octet-stream",
        file_ext=ext.lstrip("."),
        size_bytes=size_bytes,
        file_type=template_type,
        file_category=TEMPLATE_CATEGORY,
        file_role="source",
        is_submission_file=False,
        preview_metadata_json=meta,
        preview_status="ready",
    )
    db.add(record)
    commit_or_400(db, "Could not save template")
    db.refresh(record)
    return _template_to_dict(record)


@router.get("")
def list_templates(
    template_type: str | None = None,
    db: Session = Depends(get_db),
) -> list[dict]:
    stmt = select(UploadedFile).where(
        UploadedFile.file_category == TEMPLATE_CATEGORY,
        UploadedFile.deleted_at.is_(None),
    )
    templates = list(db.scalars(stmt.order_by(UploadedFile.created_at.desc())))
    result = [_template_to_dict(t) for t in templates]
    if template_type:
        result = [t for t in result if t["template_type"] == template_type]
    return result


@router.get("/{template_id}")
def get_template(template_id: str, db: Session = Depends(get_db)) -> dict:
    from uuid import UUID as _UUID
    f = db.get(UploadedFile, _UUID(template_id))
    if not f or f.file_category != TEMPLATE_CATEGORY:
        raise HTTPException(status_code=404, detail="Template not found")
    return _template_to_dict(f)


@router.get("/{template_id}/fields")
def get_template_fields(template_id: str, db: Session = Depends(get_db)) -> dict:
    from uuid import UUID as _UUID
    f = db.get(UploadedFile, _UUID(template_id))
    if not f or f.file_category != TEMPLATE_CATEGORY:
        raise HTTPException(status_code=404, detail="Template not found")

    meta = f.preview_metadata_json or {}
    fields = meta.get("placeholder_fields") or []

    # Re-extract if empty
    if not fields and f.file_ext == "hwpx":
        from app.services.file_storage_service import resolve_abs_path
        abs_path = resolve_abs_path(f)
        if abs_path.exists():
            try:
                fields = extract_hwpx_placeholders(abs_path)
                # Cache
                meta["placeholder_fields"] = fields
                f.preview_metadata_json = meta
                db.commit()
            except Exception:
                pass

    return {
        "template_id": template_id,
        "name": meta.get("template_name") or f.original_filename,
        "fields": fields,
        "ext": f.file_ext,
    }
