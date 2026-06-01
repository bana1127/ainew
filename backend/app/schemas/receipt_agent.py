from __future__ import annotations

from datetime import date
from uuid import UUID

from pydantic import BaseModel

from app.schemas.common import ORMModel


class ReceiptAnalyzeRequest(BaseModel):
    file_id: UUID | None = None
    activity_report_id: UUID | None = None
    save_to_db: bool = True
    manual_payment_method: str | None = None
    manual_category: str | None = None


class ReceiptExtractedData(ORMModel):
    receipt_date: date | None = None
    store_name: str | None = None
    amount: int = 0
    payment_method: str = "unknown"
    category: str | None = None
    raw_text: str | None = None
    confidence: float = 0.0


class ReceiptPolicyCheckResult(ORMModel):
    evidence_status: str
    need_check: bool
    required_evidence: list[str] = []
    reason: str
    rule_key: str


class ReceiptAnalyzeResponse(ORMModel):
    receipt_id: UUID | None = None
    file_id: UUID | None = None
    activity_report_id: UUID | None = None
    extracted: ReceiptExtractedData
    policy: ReceiptPolicyCheckResult
    saved: bool
    model: str
