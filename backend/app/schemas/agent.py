from __future__ import annotations

from datetime import date
from uuid import UUID

from pydantic import BaseModel

from app.schemas.common import ORMModel


class ActivityReportGenerateRequest(BaseModel):
    activity_report_id: UUID | None = None
    category_id: UUID
    reference_report_id: UUID | None = None
    title: str
    activity_date: date | None = None
    location: str | None = None
    input_text: str | None = None
    participant_ids: list[UUID] = []
    file_ids: list[UUID] = []
    save_to_db: bool = True


class ActivityReportGenerateResponse(ORMModel):
    activity_report_id: UUID | None = None
    title: str
    summary: str
    content: str
    missing_fields: list[str] = []
    confidence: float
    model: str
    saved: bool
