from __future__ import annotations

from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.file import UploadedFile
from app.routers.common import commit_or_400
from app.agents.receipt_analysis_orchestrator import ReceiptAnalysisOrchestrator, ReceiptOrchestratorInput
from app.schemas.receipt_agent import (
    ReceiptAnalyzeRequest,
    ReceiptAnalyzeResponse,
    ReceiptExtractedData,
    ReceiptPolicyCheckResult,
)

router = APIRouter()


def _save_receipt_file(file: UploadFile, db: Session) -> UploadedFile:
    settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    suffix = Path(file.filename or "").suffix.lower()
    stored_name = f"{uuid4()}{suffix}"
    stored_path = settings.UPLOAD_DIR / stored_name

    with stored_path.open("wb") as output:
        while chunk := file.file.read(1024 * 1024):
            output.write(chunk)

    record = UploadedFile(
        original_filename=file.filename or stored_name,
        stored_path=(Path("uploads") / stored_name).as_posix(),
        mime_type=file.content_type,
        file_type="receipt",
        related_entity_type="receipt",
        related_entity_id=None,
    )
    db.add(record)
    commit_or_400(db, "Could not save receipt file metadata")
    db.refresh(record)
    return record


def _orchestrate(
    db: Session,
    file_id: UUID,
    file_path: Path | None,
    file_name: str,
    mime_type: str | None,
    activity_report_id: UUID | None,
    save_to_db: bool,
    manual_payment_method: str | None,
    manual_category: str | None,
) -> ReceiptAnalyzeResponse:
    orchestrator_input = ReceiptOrchestratorInput(
        file_id=file_id,
        file_path=file_path,
        file_name=file_name,
        mime_type=mime_type,
        activity_report_id=activity_report_id,
        save_to_db=save_to_db,
        manual_payment_method=manual_payment_method,
        manual_category=manual_category,
    )

    try:
        result = ReceiptAnalysisOrchestrator(db).run(orchestrator_input)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    from datetime import date
    extracted_date = None
    if result.extracted.receipt_date:
        try:
            extracted_date = date.fromisoformat(result.extracted.receipt_date)
        except ValueError:
            pass

    return ReceiptAnalyzeResponse(
        receipt_id=result.receipt_id,
        file_id=result.file_id,
        activity_report_id=result.activity_report_id,
        extracted=ReceiptExtractedData(
            receipt_date=extracted_date,
            store_name=result.extracted.store_name,
            amount=result.extracted.amount,
            payment_method=result.extracted.payment_method,
            category=result.extracted.category,
            raw_text=result.extracted.raw_text,
            confidence=result.extracted.confidence,
        ),
        policy=ReceiptPolicyCheckResult(
            evidence_status=result.policy.evidence_status,
            need_check=result.policy.need_check,
            required_evidence=result.policy.required_evidence,
            reason=result.policy.reason,
            rule_key=result.policy.rule_key,
        ),
        saved=result.saved,
        model=result.model,
    )


@router.post("/receipt/analyze", response_model=ReceiptAnalyzeResponse)
def analyze_receipt_upload(
    file: UploadFile = File(...),
    activity_report_id: UUID | None = Form(default=None),
    save_to_db: bool = Form(default=True),
    manual_payment_method: str | None = Form(default=None),
    manual_category: str | None = Form(default=None),
    db: Session = Depends(get_db),
) -> ReceiptAnalyzeResponse:
    uploaded = _save_receipt_file(file, db)
    full_path = settings.UPLOAD_DIR.parent / uploaded.stored_path
    return _orchestrate(
        db=db,
        file_id=uploaded.id,
        file_path=full_path if full_path.exists() else None,
        file_name=uploaded.original_filename,
        mime_type=uploaded.mime_type,
        activity_report_id=activity_report_id,
        save_to_db=save_to_db,
        manual_payment_method=manual_payment_method,
        manual_category=manual_category,
    )


@router.post("/receipt/analyze-file", response_model=ReceiptAnalyzeResponse)
def analyze_receipt_by_file_id(
    payload: ReceiptAnalyzeRequest,
    db: Session = Depends(get_db),
) -> ReceiptAnalyzeResponse:
    if payload.file_id is None:
        raise HTTPException(status_code=400, detail="file_id가 필요합니다.")

    uploaded = db.get(UploadedFile, payload.file_id)
    if uploaded is None:
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")

    full_path = settings.UPLOAD_DIR.parent / uploaded.stored_path
    return _orchestrate(
        db=db,
        file_id=uploaded.id,
        file_path=full_path if full_path.exists() else None,
        file_name=uploaded.original_filename,
        mime_type=uploaded.mime_type,
        activity_report_id=payload.activity_report_id,
        save_to_db=payload.save_to_db,
        manual_payment_method=payload.manual_payment_method,
        manual_category=payload.manual_category,
    )
