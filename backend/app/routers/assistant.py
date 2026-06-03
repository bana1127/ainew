"""Assistant Command Center router.

POST /api/assistant/execute — multipart form request
  message: optional text
  requested_intent: auto | receipt_analysis | bank_statement_import | payment_matching | activity_report_generate | activity_fee_generate
  auto_apply: true/false
  period: optional string
  payment_type: optional string
  required_amount: optional integer
  activity_id: optional UUID string (Task 17)
  activity_mode: auto | link_existing | create_new | none (Task 17)
  create_activity_if_missing: boolean (Task 17)
  files: optional list of files
"""
from __future__ import annotations

import logging
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.file import UploadedFile
from app.routers.common import commit_or_400
from app.agents.assistant_orchestrator import AssistantInput, AssistantOrchestrator
from app.schemas.assistant import AssistantExecuteResponse

router = APIRouter()
logger = logging.getLogger(__name__)


def _save_file(file: UploadFile, file_type: str, db: Session) -> tuple[UploadedFile, Path]:
    """Save uploaded file to disk and return (UploadedFile record, absolute_path)."""
    settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    suffix = Path(file.filename or "").suffix.lower()
    stored_name = f"{uuid4()}{suffix}"
    stored_path = settings.UPLOAD_DIR / stored_name

    with stored_path.open("wb") as out:
        while chunk := file.file.read(1024 * 1024):
            out.write(chunk)

    from app.services.file_classification_service import classify_uploaded_file
    classification = classify_uploaded_file(file.filename or stored_name, file.content_type)
    size_bytes = stored_path.stat().st_size if stored_path.exists() else None

    record = UploadedFile(
        original_filename=file.filename or stored_name,
        stored_path=(Path("uploads") / stored_name).as_posix(),
        stored_filename=stored_name,
        mime_type=file.content_type,
        file_ext=suffix.lstrip(".") or None,
        size_bytes=size_bytes,
        file_type=file_type,
        file_category=classification.file_category,
        file_role=classification.file_role,
        related_entity_type=None,
        related_entity_id=None,
    )
    db.add(record)
    commit_or_400(db, "Could not save assistant file")
    db.refresh(record)
    return record, stored_path


@router.post("/execute", response_model=AssistantExecuteResponse)
async def execute(
    message: str | None = Form(default=None),
    requested_intent: str = Form(default="auto"),
    auto_apply: bool = Form(default=False),
    period: str = Form(default="2026-1"),
    payment_type: str = Form(default="membership_fee"),
    required_amount: int = Form(default=30000),
    # Task 17: Activity-aware fields
    activity_id: str | None = Form(default=None),
    activity_mode: str = Form(default="auto"),
    create_activity_if_missing: bool = Form(default=False),
    files: list[UploadFile] = File(default=[]),
    db: Session = Depends(get_db),
) -> AssistantExecuteResponse:
    """Execute an assistant task.

    Saves any uploaded files, routes by intent, and returns a standardised result.
    Task 17: Activity Resolver runs first to determine activity context.
    """
    IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
    BANK_EXTS = {".xls", ".xlsx", ".csv"}

    file_ids = []
    file_names = []
    file_paths = []
    mime_types = []

    for f in files:
        if not f.filename:
            continue
        ext = Path(f.filename).suffix.lower()
        if ext in BANK_EXTS:
            file_type = "bank_statement"
        elif ext in IMAGE_EXTS:
            file_type = "receipt"
        else:
            file_type = "other"

        record, abs_path = _save_file(f, file_type, db)
        file_ids.append(record.id)
        file_names.append(f.filename)
        file_paths.append(abs_path)
        mime_types.append(f.content_type)

    logger.warning("[assistant] uploaded_files_count=%s", len(file_ids))
    logger.warning("[assistant] saved_file_ids=%s", [str(fid) for fid in file_ids])

    # Parse activity_id
    parsed_activity_id: UUID | None = None
    if activity_id:
        try:
            parsed_activity_id = UUID(activity_id)
        except (ValueError, AttributeError):
            logger.warning("Invalid activity_id format: %s", activity_id)

    # When activity_id is explicitly provided (e.g. from activity detail AI tab),
    # pre-link uploaded files to that activity so they appear in the file vault.
    if parsed_activity_id and file_ids:
        for fid in file_ids:
            record = db.get(UploadedFile, fid)
            if record and not record.activity_report_id:
                record.activity_report_id = parsed_activity_id
                record.related_entity_type = "activity_report"
                record.related_entity_id = parsed_activity_id
        db.commit()

    # Task 25: Human-in-the-loop — auto_apply is always False regardless of input.
    inp = AssistantInput(
        message=message,
        file_ids=file_ids,
        file_names=file_names,
        file_paths=file_paths,
        mime_types=mime_types,
        requested_intent=requested_intent,
        auto_apply=False,
        period=period,
        payment_type=payment_type,
        required_amount=required_amount,
        activity_id=parsed_activity_id,
        activity_mode=activity_mode,
        create_activity_if_missing=create_activity_if_missing,
    )

    return AssistantOrchestrator(db).run(inp)


@router.post("/actions/{action_id}/confirm")
def confirm_assistant_action(
    action_id: UUID,
    db: Session = Depends(get_db),
) -> dict:
    from app.services.assistant_action_service import confirm_action_proposal

    try:
        proposal, result = confirm_action_proposal(db, action_id)
    except ValueError as exc:
        msg = str(exc)
        status_code = 404 if "not found" in msg.lower() else 400
        raise HTTPException(status_code=status_code, detail=msg)

    return {
        "ok": True,
        "action_id": str(proposal.id),
        "action_type": proposal.action_type,
        "status": proposal.status,
        "activity_id": str(proposal.activity_id) if proposal.activity_id else None,
        "result": result,
    }


@router.post("/actions/{action_id}/cancel")
def cancel_assistant_action(
    action_id: UUID,
    db: Session = Depends(get_db),
) -> dict:
    from app.services.assistant_action_service import cancel_action_proposal

    try:
        proposal = cancel_action_proposal(db, action_id)
    except ValueError as exc:
        msg = str(exc)
        status_code = 404 if "not found" in msg.lower() else 400
        raise HTTPException(status_code=status_code, detail=msg)

    return {
        "ok": True,
        "action_id": str(proposal.id),
        "action_type": proposal.action_type,
        "status": proposal.status,
        "activity_id": str(proposal.activity_id) if proposal.activity_id else None,
    }
