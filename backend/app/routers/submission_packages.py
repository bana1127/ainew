"""Submission package management router.

GET  /preview?month=YYYY-MM  — preview what would be included
POST /generate               — create ZIP and return download URL
"""
from __future__ import annotations

import calendar
import io
import zipfile
from datetime import date, datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models import ActivityReport
from app.models.file import UploadedFile
from app.routers.common import commit_or_400
from app.services.file_storage_service import resolve_abs_path


router = APIRouter()


REQUIRED_CATEGORIES = ["activity_report", "activity_plan", "receipt"]


def _get_club_name() -> str:
    return getattr(settings, "CLUB_NAME", "ClubAgent")


def _activities_in_month(db: Session, month: str) -> list[ActivityReport]:
    """Return activities whose activity_date falls in the given month (YYYY-MM)."""
    try:
        year, mon = month.split("-")
        year_int, mon_int = int(year), int(mon)
    except ValueError:
        return []

    last_day = calendar.monthrange(year_int, mon_int)[1]
    start = date(year_int, mon_int, 1)
    end = date(year_int, mon_int, last_day)

    return list(db.scalars(
        select(ActivityReport).where(
            and_(
                ActivityReport.activity_date >= start,
                ActivityReport.activity_date <= end,
                ActivityReport.deleted_at.is_(None),
            )
        ).order_by(ActivityReport.activity_date)
    ))


@router.get("/preview")
def preview_submission_package(
    month: str = Query(..., description="YYYY-MM"),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    activities = _activities_in_month(db, month)
    activity_items = []
    total_submission_files = 0
    total_missing = 0

    for act in activities:
        files = list(db.scalars(
            select(UploadedFile).where(
                and_(
                    UploadedFile.activity_report_id == act.id,
                    UploadedFile.is_submission_file.is_(True),
                    UploadedFile.deleted_at.is_(None),
                )
            )
        ))

        present_categories = {f.file_category for f in files}
        missing = [cat for cat in REQUIRED_CATEGORIES if cat not in present_categories]
        total_submission_files += len(files)
        total_missing += len(missing)

        activity_items.append({
            "activity_id": str(act.id),
            "title": act.title,
            "activity_date": str(act.activity_date) if act.activity_date else None,
            "submission_files": [
                {
                    "id": str(f.id),
                    "filename": f.original_filename,
                    "category": f.file_category,
                    "role": f.file_role,
                    "size_bytes": f.size_bytes,
                }
                for f in files
            ],
            "missing_items": missing,
        })

    return {
        "month": month,
        "activities": activity_items,
        "summary": {
            "activity_count": len(activities),
            "submission_file_count": total_submission_files,
            "missing_count": total_missing,
        },
    }


class GeneratePayload(BaseModel):
    month: str
    include_categories: list[str] = ["activity_report", "activity_plan", "receipt", "attachment"]


@router.post("/generate")
def generate_submission_package(
    payload: GeneratePayload,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    activities = _activities_in_month(db, payload.month)
    if not activities:
        raise HTTPException(status_code=404, detail=f"{payload.month}에 해당하는 활동이 없습니다.")

    club_name = _get_club_name()
    zip_buffer = io.BytesIO()
    file_count = 0

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for act in activities:
            stmt = select(UploadedFile).where(
                and_(
                    UploadedFile.activity_report_id == act.id,
                    UploadedFile.is_submission_file.is_(True),
                    UploadedFile.deleted_at.is_(None),
                )
            )
            if payload.include_categories:
                stmt = stmt.where(UploadedFile.file_category.in_(payload.include_categories))

            files = list(db.scalars(stmt))
            if not files:
                continue

            date_str = (act.activity_date or "").replace("-", "") if act.activity_date else "unknown"
            safe_title = act.title.replace("/", "_").replace("\\", "_")[:30]

            for f in files:
                abs_path = resolve_abs_path(f)
                if not abs_path.exists():
                    continue
                ext = f.file_ext or abs_path.suffix.lstrip(".")
                zip_filename = f"{club_name}_{date_str}_{safe_title}.{ext}"
                # If multiple files with same name, append index
                existing = [n for n in zf.namelist() if n == zip_filename]
                if existing:
                    zip_filename = f"{club_name}_{date_str}_{safe_title}_{file_count}.{ext}"

                zf.write(abs_path, arcname=zip_filename)
                file_count += 1

    if file_count == 0:
        raise HTTPException(status_code=400, detail="제출용 파일이 없습니다. 파일을 제출용으로 지정해 주세요.")

    zip_buffer.seek(0)
    zip_bytes = zip_buffer.read()

    # Save zip to uploads dir
    settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    zip_name = f"submission_{payload.month}_{uuid4().hex[:8]}.zip"
    zip_path = settings.UPLOAD_DIR / zip_name
    zip_path.write_bytes(zip_bytes)

    from pathlib import Path
    try:
        rel_path = zip_path.relative_to(settings.UPLOAD_DIR.parent)
    except ValueError:
        rel_path = Path("uploads") / zip_name

    record = UploadedFile(
        original_filename=f"submission_{payload.month}.zip",
        stored_path=rel_path.as_posix(),
        stored_filename=zip_name,
        mime_type="application/zip",
        file_ext="zip",
        size_bytes=len(zip_bytes),
        file_type="submission_package",
        file_category="submission_package",
        file_role="generated",
        is_submission_file=False,
        submission_month=payload.month,
        preview_status="pending",
    )
    db.add(record)
    commit_or_400(db, "Could not save ZIP record")
    db.refresh(record)

    return {
        "ok": True,
        "package_file_id": str(record.id),
        "month": payload.month,
        "file_count": file_count,
        "download_url": f"/api/files/{record.id}/download",
    }
