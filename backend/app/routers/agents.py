from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.activity import ActivityCategory, ActivityReport, ReferenceReport
from app.models.member import Member
from app.models.file import UploadedFile
from app.agents.activity_report_orchestrator import ActivityReportOrchestrator, OrchestratorInput
from app.schemas.agent import ActivityReportGenerateRequest, ActivityReportGenerateResponse

router = APIRouter()


@router.post("/activity-report/generate", response_model=ActivityReportGenerateResponse)
def generate_activity_report(
    payload: ActivityReportGenerateRequest,
    db: Session = Depends(get_db),
) -> ActivityReportGenerateResponse:
    # 1. Validate category_id
    category = db.get(ActivityCategory, payload.category_id)
    if category is None:
        raise HTTPException(status_code=404, detail="활동 카테고리를 찾을 수 없습니다.")

    # 2. Get reference report content if provided
    reference_content: str | None = None
    if payload.reference_report_id is not None:
        ref = db.get(ReferenceReport, payload.reference_report_id)
        if ref is not None:
            reference_content = ref.content

    # 3. Get participant names
    participant_names: list[str] = []
    if payload.participant_ids:
        members = db.execute(
            select(Member).where(Member.id.in_(payload.participant_ids))
        ).scalars().all()
        participant_names = [m.name for m in members]

    # 4. Build orchestrator input
    orchestrator_input = OrchestratorInput(
        category_id=payload.category_id,
        title=payload.title,
        category_name=category.name,
        report_template=category.report_template,
        reference_content=reference_content,
        activity_date=payload.activity_date.isoformat() if payload.activity_date else None,
        location=payload.location,
        input_text=payload.input_text,
        participant_names=participant_names,
        file_ids=list(payload.file_ids),
        activity_report_id=payload.activity_report_id,
        save_to_db=payload.save_to_db,
    )

    # 5. Run orchestrator
    try:
        result = ActivityReportOrchestrator(db).run(orchestrator_input)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    # 6. Return response
    return ActivityReportGenerateResponse(
        activity_report_id=result.activity_report_id,
        title=result.title,
        summary=result.summary,
        content=result.content,
        missing_fields=result.missing_fields,
        confidence=result.confidence,
        model=result.model,
        saved=result.saved,
    )
