from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import ActivityCategory, ReferenceReport
from app.routers.common import apply_updates, commit_or_400, get_or_404
from app.schemas import ReferenceReportCreate, ReferenceReportRead, ReferenceReportUpdate


router = APIRouter()


def ensure_category(db: Session, category_id: UUID | None) -> None:
    if category_id and db.get(ActivityCategory, category_id) is None:
        raise HTTPException(status_code=404, detail="Activity category not found")


@router.get("", response_model=list[ReferenceReportRead])
def list_reference_reports(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    category_id: UUID | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
) -> list[ReferenceReport]:
    statement = select(ReferenceReport)
    if category_id:
        statement = statement.where(ReferenceReport.category_id == category_id)
    if q:
        pattern = f"%{q}%"
        statement = statement.where(
            or_(ReferenceReport.title.ilike(pattern), ReferenceReport.content.ilike(pattern))
        )
    return list(db.scalars(statement.offset(skip).limit(limit)))


@router.post("", response_model=ReferenceReportRead)
def create_reference_report(
    payload: ReferenceReportCreate,
    db: Session = Depends(get_db),
) -> ReferenceReport:
    ensure_category(db, payload.category_id)
    report = ReferenceReport(**payload.model_dump())
    db.add(report)
    commit_or_400(db, "Could not create reference report")
    db.refresh(report)
    return report


@router.get("/{reference_id}", response_model=ReferenceReportRead)
def get_reference_report(
    reference_id: UUID,
    db: Session = Depends(get_db),
) -> ReferenceReport:
    return get_or_404(db, ReferenceReport, reference_id, "Reference report")


@router.patch("/{reference_id}", response_model=ReferenceReportRead)
def update_reference_report(
    reference_id: UUID,
    payload: ReferenceReportUpdate,
    db: Session = Depends(get_db),
) -> ReferenceReport:
    report = get_or_404(db, ReferenceReport, reference_id, "Reference report")
    data = payload.model_dump(exclude_unset=True)
    ensure_category(db, data.get("category_id"))
    apply_updates(report, payload)
    commit_or_400(db, "Could not update reference report")
    db.refresh(report)
    return report


@router.delete("/{reference_id}", response_model=ReferenceReportRead)
def delete_reference_report(
    reference_id: UUID,
    db: Session = Depends(get_db),
) -> ReferenceReport:
    report = get_or_404(db, ReferenceReport, reference_id, "Reference report")
    db.delete(report)
    commit_or_400(db, "Could not delete reference report")
    return report

