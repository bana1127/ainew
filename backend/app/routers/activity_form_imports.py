"""Google Form 응답 엑셀 Import API.

POST /api/activity-form-imports/preview  - 미리보기 (DB 미반영)
POST /api/activity-form-imports/apply    - 실제 반영
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.google_form_import_service import (
    ImportRow,
    apply_import,
    preview_import,
)

router = APIRouter()

ALLOWED_EXTENSIONS = {".xls", ".xlsx", ".csv"}


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class ImportActivityContextOut(BaseModel):
    mode: str
    activity_id: str | None = None
    activity_title: str | None = None


class ImportSummaryOut(BaseModel):
    total_rows: int
    matched_members: int
    new_member_candidates: int
    needs_review: int
    existing_participants: int
    new_participants: int


class ImportRowOut(BaseModel):
    row_index: int
    name: str | None
    student_id: str | None
    phone: str | None
    email: str | None
    department: str | None
    submitted_at: str | None
    member_match_status: str
    member_id: str | None
    participant_action: str
    participant_status: str
    raw_response: dict[str, Any]


class ImportPreviewOut(BaseModel):
    import_id: str
    form_type: str
    confidence: float
    matched_columns: list[str]
    activity_context: ImportActivityContextOut
    summary: ImportSummaryOut
    rows: list[ImportRowOut]
    requires_confirmation: bool


class ImportApplyPayload(BaseModel):
    import_id: str | None = None
    activity_id: str
    form_type: str
    rows: list[dict[str, Any]] = []


class ImportApplyOut(BaseModel):
    ok: bool
    activity_id: str
    form_type: str
    created_members: int
    updated_members: int
    created_participants: int
    updated_participants: int
    saved_feedbacks: int


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/preview", response_model=ImportPreviewOut)
async def activity_form_import_preview(
    file: UploadFile = File(...),
    activity_id: str | None = Form(default=None),
    form_stage: str = Form(default="auto"),
    activity_mode: str = Form(default="auto"),
    db: Session = Depends(get_db),
) -> ImportPreviewOut:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"지원하지 않는 파일 형식: {suffix}. 지원: .xls, .xlsx, .csv",
        )

    file_bytes = await file.read()
    filename = file.filename or "upload"

    try:
        result = preview_import(
            db=db,
            file_bytes=file_bytes,
            filename=filename,
            activity_id=activity_id,
            form_stage=form_stage,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"파일 처리 중 오류: {e}")

    return ImportPreviewOut(
        import_id=result.import_id,
        form_type=result.form_type,
        confidence=result.confidence,
        matched_columns=result.matched_columns,
        activity_context=ImportActivityContextOut(
            mode=result.activity_context.mode,
            activity_id=result.activity_context.activity_id,
            activity_title=result.activity_context.activity_title,
        ),
        summary=ImportSummaryOut(
            total_rows=result.summary.total_rows,
            matched_members=result.summary.matched_members,
            new_member_candidates=result.summary.new_member_candidates,
            needs_review=result.summary.needs_review,
            existing_participants=result.summary.existing_participants,
            new_participants=result.summary.new_participants,
        ),
        rows=[
            ImportRowOut(
                row_index=r.row_index,
                name=r.name,
                student_id=r.student_id,
                phone=r.phone,
                email=r.email,
                department=r.department,
                submitted_at=r.submitted_at,
                member_match_status=r.member_match_status,
                member_id=r.member_id,
                participant_action=r.participant_action,
                participant_status=r.participant_status,
                raw_response=r.raw_response,
            )
            for r in result.rows
        ],
        requires_confirmation=result.requires_confirmation,
    )


@router.post("/apply", response_model=ImportApplyOut)
def activity_form_import_apply(
    payload: ImportApplyPayload,
    db: Session = Depends(get_db),
) -> ImportApplyOut:
    if not payload.activity_id:
        raise HTTPException(status_code=400, detail="activity_id는 필수입니다.")

    # Convert dict rows to ImportRow objects
    rows: list[ImportRow] = []
    for r in payload.rows:
        rows.append(
            ImportRow(
                row_index=r.get("row_index", 0),
                name=r.get("name"),
                student_id=r.get("student_id"),
                phone=r.get("phone"),
                email=r.get("email"),
                department=r.get("department"),
                submitted_at=r.get("submitted_at"),
                member_match_status=r.get("member_match_status", "new"),
                member_id=r.get("member_id"),
                participant_action=r.get("participant_action", "create"),
                participant_status=r.get("participant_status", "applied"),
                raw_response=r.get("raw_response", {}),
            )
        )

    try:
        result = apply_import(
            db=db,
            activity_id=payload.activity_id,
            form_type=payload.form_type,
            rows=rows,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import 처리 중 오류: {e}")

    return ImportApplyOut(
        ok=result.ok,
        activity_id=result.activity_id,
        form_type=result.form_type,
        created_members=result.created_members,
        updated_members=result.updated_members,
        created_participants=result.created_participants,
        updated_participants=result.updated_participants,
        saved_feedbacks=result.saved_feedbacks,
    )
