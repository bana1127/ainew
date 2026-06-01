"""Automation endpoints — callable by n8n or any HTTP client.

Authentication:
  If AUTOMATION_API_TOKEN is set, all requests must include
  X-Automation-Token: <token> header. Otherwise open access.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.services.automation_service import (
    run_audit_check,
    run_quarterly_summary,
    run_weekly_check,
)

router = APIRouter()


def _verify_token(x_automation_token: str | None = Header(default=None)) -> None:
    """Dependency: verifies automation token if configured."""
    expected = settings.AUTOMATION_API_TOKEN
    if expected:
        if x_automation_token is None or x_automation_token != expected:
            raise HTTPException(status_code=401, detail="Invalid or missing automation token")


class WeeklyCheckResponse(BaseModel):
    ok: bool
    pending_receipts: int
    unpaid_members: int
    unmatched_transactions: int
    draft_reports: int
    unread_notifications: int
    items: list[str]
    severity: str
    notification_saved: bool


class AuditCheckResponse(BaseModel):
    ok: bool
    need_check_receipts: int
    invalid_receipts: int
    zero_amount_receipts: int
    unlinked_receipts: int
    items: list[str]
    severity: str
    notification_saved: bool


class QuarterlySummaryResponse(BaseModel):
    ok: bool
    year: int
    quarter: int
    activity_reports: int
    receipts: int
    total_deposit: int
    total_withdraw: int
    unpaid_count: int
    need_check_receipts: int
    severity: str
    notification_saved: bool


@router.post("/weekly-check", response_model=WeeklyCheckResponse)
def weekly_check(
    db: Session = Depends(get_db),
    _: None = Depends(_verify_token),
) -> WeeklyCheckResponse:
    """Run weekly operations check and store results in Notifications."""
    result = run_weekly_check(db)
    return WeeklyCheckResponse(
        ok=True,
        pending_receipts=result.pending_receipts,
        unpaid_members=result.unpaid_members,
        unmatched_transactions=result.unmatched_transactions,
        draft_reports=result.draft_reports,
        unread_notifications=result.unread_notifications,
        items=result.items,
        severity=result.severity,
        notification_saved=True,
    )


@router.post("/audit-check", response_model=AuditCheckResponse)
def audit_check(
    db: Session = Depends(get_db),
    _: None = Depends(_verify_token),
) -> AuditCheckResponse:
    """Run audit compliance check and store results in Notifications."""
    result = run_audit_check(db)
    return AuditCheckResponse(
        ok=True,
        need_check_receipts=result.need_check_receipts,
        invalid_receipts=result.invalid_receipts,
        zero_amount_receipts=result.zero_amount_receipts,
        unlinked_receipts=result.unlinked_receipts,
        items=result.items,
        severity=result.severity,
        notification_saved=True,
    )


@router.post("/quarterly-summary", response_model=QuarterlySummaryResponse)
def quarterly_summary(
    year: int | None = Query(default=None),
    quarter: int | None = Query(default=None),
    db: Session = Depends(get_db),
    _: None = Depends(_verify_token),
) -> QuarterlySummaryResponse:
    """Generate quarterly summary and store in Notifications."""
    result = run_quarterly_summary(db, year=year, quarter=quarter)
    return QuarterlySummaryResponse(
        ok=True,
        year=result.year,
        quarter=result.quarter,
        activity_reports=result.activity_reports,
        receipts=result.receipts,
        total_deposit=result.total_deposit,
        total_withdraw=result.total_withdraw,
        unpaid_count=result.unpaid_count,
        need_check_receipts=result.need_check_receipts,
        severity=result.severity,
        notification_saved=True,
    )
