"""Automation service for periodic checks.

Functions here are called by /api/automations/* endpoints,
which can be triggered by n8n or any HTTP client.

Each function:
  1. Queries the DB for relevant data.
  2. Builds a human-readable summary.
  3. Creates a Notification record so results are visible in the UI.
  4. Returns a structured dict for the API response.

TODO(Task 15): Store full item lists in a JSON metadata column once
  the notifications table has a `payload` field.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.models.activity import ActivityReport, ReferenceReport
from app.models.notification import Notification
from app.models.payment import PaymentRecord
from app.models.receipt import Receipt
from app.models.transaction import BankTransaction

logger = logging.getLogger(__name__)


def _save_notification(
    db: Session,
    title: str,
    message: str,
    severity: str = "info",
) -> None:
    notif = Notification(
        type="automation",
        title=title,
        message=message,
        severity=severity,
        is_read=False,
    )
    db.add(notif)
    db.commit()


# ---------------------------------------------------------------------------
# weekly-check
# ---------------------------------------------------------------------------

@dataclass
class WeeklyCheckResult:
    pending_receipts: int = 0
    unpaid_members: int = 0
    unmatched_transactions: int = 0
    draft_reports: int = 0
    unread_notifications: int = 0
    items: list[str] = field(default_factory=list)
    severity: str = "info"


def run_weekly_check(db: Session) -> WeeklyCheckResult:
    result = WeeklyCheckResult()
    items: list[str] = []

    # 확인 필요 영수증
    pending = db.scalar(
        select(Receipt).where(Receipt.evidence_status == "need_check").with_only_columns(
            Receipt.id.label("count")
        ).correlate_except(Receipt)
    )
    pending_receipts = db.execute(
        select(Receipt).where(Receipt.evidence_status == "need_check")
    ).scalars().all()
    result.pending_receipts = len(pending_receipts)
    if result.pending_receipts:
        items.append(f"확인 필요 영수증 {result.pending_receipts}건")

    # 미납자
    unpaid_records = db.execute(
        select(PaymentRecord).where(PaymentRecord.status.in_(["unpaid", "partial"]))
    ).scalars().all()
    result.unpaid_members = len(unpaid_records)
    if result.unpaid_members:
        items.append(f"미납/부분납부 {result.unpaid_members}건")

    # 미매칭 거래
    unmatched = db.execute(
        select(BankTransaction).where(BankTransaction.match_status == "unmatched")
    ).scalars().all()
    result.unmatched_transactions = len(unmatched)
    if result.unmatched_transactions:
        items.append(f"미매칭 거래 {result.unmatched_transactions}건")

    # 초안/생성됨 보고서
    draft_reports = db.execute(
        select(ActivityReport).where(ActivityReport.status.in_(["draft", "generated"]))
    ).scalars().all()
    result.draft_reports = len(draft_reports)
    if result.draft_reports:
        items.append(f"작성 중 보고서 {result.draft_reports}건")

    # 읽지 않은 알림
    unread = db.execute(
        select(Notification).where(
            and_(Notification.is_read.is_(False), Notification.type != "automation")
        )
    ).scalars().all()
    result.unread_notifications = len(unread)
    if result.unread_notifications:
        items.append(f"읽지 않은 알림 {result.unread_notifications}건")

    result.items = items
    result.severity = "warning" if items else "info"

    msg_body = "이번 주 점검 결과 처리 항목이 없습니다." if not items else "처리 필요: " + " / ".join(items)
    title = "주간 자동 점검 완료"
    _save_notification(db, title=title, message=msg_body, severity=result.severity)

    return result


# ---------------------------------------------------------------------------
# audit-check
# ---------------------------------------------------------------------------

@dataclass
class AuditCheckResult:
    need_check_receipts: int = 0
    invalid_receipts: int = 0
    zero_amount_receipts: int = 0
    unlinked_receipts: int = 0
    items: list[str] = field(default_factory=list)
    severity: str = "info"


def run_audit_check(db: Session) -> AuditCheckResult:
    result = AuditCheckResult()
    items: list[str] = []

    # need_check 영수증
    need_check = db.execute(
        select(Receipt).where(Receipt.evidence_status == "need_check")
    ).scalars().all()
    result.need_check_receipts = len(need_check)
    if result.need_check_receipts:
        items.append(f"감사 확인 필요 영수증 {result.need_check_receipts}건")

    # invalid 영수증
    invalid = db.execute(
        select(Receipt).where(Receipt.evidence_status == "invalid")
    ).scalars().all()
    result.invalid_receipts = len(invalid)
    if result.invalid_receipts:
        items.append(f"부적합 영수증 {result.invalid_receipts}건")

    # 금액 0 영수증
    zero_amt = db.execute(
        select(Receipt).where(Receipt.amount == 0)
    ).scalars().all()
    result.zero_amount_receipts = len(zero_amt)
    if result.zero_amount_receipts:
        items.append(f"금액 0원 영수증 {result.zero_amount_receipts}건")

    # 활동 보고서 미연결 영수증
    unlinked = db.execute(
        select(Receipt).where(Receipt.activity_report_id.is_(None))
    ).scalars().all()
    result.unlinked_receipts = len(unlinked)
    if result.unlinked_receipts:
        items.append(f"보고서 미연결 영수증 {result.unlinked_receipts}건")

    result.items = items
    result.severity = "warning" if (result.need_check_receipts or result.invalid_receipts) else "info"

    msg_body = "감사 점검 결과 이상 없음" if not items else "감사 점검: " + " / ".join(items)
    _save_notification(db, title="감사 규정 자동 점검 완료", message=msg_body, severity=result.severity)

    return result


# ---------------------------------------------------------------------------
# quarterly-summary
# ---------------------------------------------------------------------------

@dataclass
class QuarterlySummaryResult:
    year: int = 0
    quarter: int = 0
    activity_reports: int = 0
    receipts: int = 0
    total_deposit: int = 0
    total_withdraw: int = 0
    unpaid_count: int = 0
    need_check_receipts: int = 0
    severity: str = "info"


def run_quarterly_summary(
    db: Session,
    year: int | None = None,
    quarter: int | None = None,
) -> QuarterlySummaryResult:
    now = datetime.now(tz=timezone.utc)
    if year is None:
        year = now.year
    if quarter is None:
        quarter = (now.month - 1) // 3 + 1

    # Quarter month range
    q_start_month = (quarter - 1) * 3 + 1
    q_end_month = q_start_month + 2
    q_start = datetime(year, q_start_month, 1, tzinfo=timezone.utc)
    if q_end_month == 12:
        q_end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        q_end = datetime(year, q_end_month + 1, 1, tzinfo=timezone.utc)

    result = QuarterlySummaryResult(year=year, quarter=quarter)

    # 활동 보고서
    reports = db.execute(
        select(ActivityReport).where(
            and_(
                ActivityReport.created_at >= q_start,
                ActivityReport.created_at < q_end,
            )
        )
    ).scalars().all()
    result.activity_reports = len(reports)

    # 영수증
    receipts = db.execute(
        select(Receipt).where(
            and_(Receipt.created_at >= q_start, Receipt.created_at < q_end)
        )
    ).scalars().all()
    result.receipts = len(receipts)
    result.need_check_receipts = sum(1 for r in receipts if r.evidence_status == "need_check")

    # 거래
    transactions = db.execute(
        select(BankTransaction).where(
            and_(
                BankTransaction.created_at >= q_start,
                BankTransaction.created_at < q_end,
            )
        )
    ).scalars().all()
    result.total_deposit = sum(t.deposit_amount or 0 for t in transactions)
    result.total_withdraw = sum(t.withdraw_amount or 0 for t in transactions)

    # 미납
    unpaid = db.execute(
        select(PaymentRecord).where(PaymentRecord.status.in_(["unpaid", "partial"]))
    ).scalars().all()
    result.unpaid_count = len(unpaid)

    msg = (
        f"{year}년 {quarter}분기 요약: "
        f"활동보고서 {result.activity_reports}건, "
        f"영수증 {result.receipts}건, "
        f"입금 {result.total_deposit:,}원, "
        f"출금 {result.total_withdraw:,}원, "
        f"미납 {result.unpaid_count}건, "
        f"확인필요증빙 {result.need_check_receipts}건"
    )
    _save_notification(
        db,
        title=f"{year}년 {quarter}분기 운영 요약",
        message=msg,
        severity="info",
    )

    return result
