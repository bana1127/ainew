"""Activity Fee Transaction Matching Service (Task 30).

Dedicated service for matching bank transactions against activity_fee PaymentRecords
scoped to a specific activity_id.

Rules:
  - Only activity_fee records for the given activity are considered
  - Only exact amount matches become auto_match_candidate
  - Preview never modifies DB
  - Confirm revalidates scope/type/amount before applying
  - membership_fee records are never touched
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.orm import Session


# Row-level match status values
# auto_match_candidate  - exact amount + name match → apply on confirm
# amount_mismatch       - name found but amount differs → needs user action
# name_check_required   - amount matches but name uncertain → needs user confirmation
# already_paid          - payment_record already paid/exempt
# already_matched       - transaction already linked to another record
# unmatched             - no viable candidate
MATCH_STATUS_VALUES = {
    "auto_match_candidate",
    "amount_mismatch",
    "name_check_required",
    "already_paid",
    "already_matched",
    "unmatched",
}


@dataclass
class ActivityFeeMatchRow:
    transaction_id: str
    transaction_datetime: str | None
    memo: str | None
    deposit_amount: int
    matched_member_id: str | None
    matched_member_name: str | None
    payment_record_id: str | None
    required_amount: int | None
    amount_difference: int | None
    match_status: str  # see MATCH_STATUS_VALUES
    score: float | None
    reason: str


@dataclass
class ActivityFeeMatchSummary:
    activity_id: str
    period: str
    total_transactions: int
    auto_match_candidates: int
    amount_mismatch: int
    name_check_required: int
    already_paid: int
    already_matched: int
    unmatched: int
    excluded_transactions: int = 0


@dataclass
class ActivityFeeMatchPreviewResult:
    activity_id: str
    summary: ActivityFeeMatchSummary
    rows: list[ActivityFeeMatchRow]
    action_id: str  # AssistantActionProposal id
    requires_confirmation: bool = True
    auto_apply: bool = False


@dataclass
class ActivityFeeMatchConfirmResult:
    ok: bool
    activity_id: str
    matched_count: int
    skipped_count: int  # already paid, amount mismatch, etc.
    updated_payment_records: int
    updated_transactions: int


# ---------------------------------------------------------------------------
# Preview
# ---------------------------------------------------------------------------

def preview_activity_fee_transaction_matching(
    db: Session,
    activity_id: UUID,
) -> ActivityFeeMatchPreviewResult:
    """Preview matching — never modifies DB. Creates a proposal for confirm step."""
    from app.models.activity import ActivityReport
    from app.models import BankTransaction, Member, PaymentRecord
    from app.models.transaction_match_exclusion import TransactionMatchExclusion
    from app.services.payment_matching_service import (
        _run_activity_fee_matching,
        is_excluded_transaction,
        normalize_memo,
    )
    from app.services.assistant_action_service import create_action_proposal

    report = db.get(ActivityReport, activity_id)
    if not report:
        raise ValueError(f"활동을 찾을 수 없습니다: {activity_id}")

    period_key = f"act-{str(activity_id)[:8]}"

    # Get activity_fee payment records for this activity only
    fee_records = list(db.scalars(
        select(PaymentRecord).where(
            and_(
                PaymentRecord.period == period_key,
                PaymentRecord.payment_type == "activity_fee",
            )
        )
    ))

    # Get member map
    member_ids = {r.member_id for r in fee_records if r.member_id}
    member_map: dict[UUID, Member] = {}
    if member_ids:
        for m in db.scalars(select(Member).where(Member.id.in_(member_ids))):
            member_map[m.id] = m

    # Build record map: member_id -> record
    record_map: dict[UUID, PaymentRecord] = {r.member_id: r for r in fee_records if r.member_id}

    # Get excluded transaction ids for this activity + activity_fee scope
    excluded_tx_ids: set[UUID] = set(
        row.transaction_id
        for row in db.scalars(
            select(TransactionMatchExclusion).where(
                and_(
                    TransactionMatchExclusion.activity_report_id == activity_id,
                    TransactionMatchExclusion.payment_type == "activity_fee",
                    TransactionMatchExclusion.is_active.is_(True),
                )
            )
        )
    )

    # Get all unmatched deposit transactions
    transactions = list(db.scalars(
        select(BankTransaction).where(
            and_(
                BankTransaction.deposit_amount > 0,
                BankTransaction.match_status != "excluded",
            )
        )
    ))

    # Get already-matched transaction ids
    matched_tx_ids: set[UUID] = {
        r.transaction_id for r in fee_records if r.transaction_id is not None
    }
    # Also include transactions matched to any other record
    all_matched_tx_ids: set[UUID] = set(
        row.transaction_id
        for row in db.scalars(
            select(PaymentRecord).where(PaymentRecord.transaction_id.isnot(None))
        )
        if row.transaction_id is not None
    )

    rows: list[ActivityFeeMatchRow] = []
    excluded_count = 0

    for txn in transactions:
        memo = txn.memo or ""
        deposit = int(txn.deposit_amount or 0)

        # Skip transactions excluded for this activity's activity_fee scope
        if txn.id in excluded_tx_ids:
            excluded_count += 1
            continue

        # Skip excluded transactions (global exclusion patterns)
        excluded, _ = is_excluded_transaction(memo, txn.transaction_type)
        if excluded:
            continue

        # Check if transaction already matched to any record
        if txn.id in all_matched_tx_ids:
            rows.append(ActivityFeeMatchRow(
                transaction_id=str(txn.id),
                transaction_datetime=txn.transaction_datetime.isoformat() if txn.transaction_datetime else None,
                memo=memo,
                deposit_amount=deposit,
                matched_member_id=None,
                matched_member_name=None,
                payment_record_id=None,
                required_amount=None,
                amount_difference=None,
                match_status="already_matched",
                score=None,
                reason="이 거래는 이미 다른 납부 기록에 연결되어 있습니다",
            ))
            continue

        # Try to match each unpaid fee record
        best_score = 0.0
        best_member: Member | None = None
        best_record: PaymentRecord | None = None
        candidates: list[tuple[float, Member, PaymentRecord]] = []

        norm_memo = normalize_memo(memo)

        for rec in fee_records:
            if not rec.member_id:
                continue
            member = member_map.get(rec.member_id)
            if not member:
                continue

            # Score: name match in memo
            name = member.name or ""
            score = 0.0
            if name and name in memo:
                score = 3.0
            elif name and name in norm_memo:
                score = 2.0
            elif name and _fuzzy_name_score(name, norm_memo) > 0.6:
                score = 1.0

            if score > 0:
                candidates.append((score, member, rec))

        candidates.sort(key=lambda x: x[0], reverse=True)

        if candidates:
            best_score, best_member, best_record = candidates[0]
            required = int(best_record.required_amount or 0)

            # Already paid check
            if best_record.status in ("paid", "exempt"):
                rows.append(ActivityFeeMatchRow(
                    transaction_id=str(txn.id),
                    transaction_datetime=txn.transaction_datetime.isoformat() if txn.transaction_datetime else None,
                    memo=memo,
                    deposit_amount=deposit,
                    matched_member_id=str(best_member.id),
                    matched_member_name=best_member.name,
                    payment_record_id=str(best_record.id),
                    required_amount=required,
                    amount_difference=deposit - required,
                    match_status="already_paid",
                    score=round(best_score, 2),
                    reason=f"{best_member.name} 이미 납부 완료",
                ))
                continue

            # Exact amount match → auto_match_candidate
            if deposit == required:
                rows.append(ActivityFeeMatchRow(
                    transaction_id=str(txn.id),
                    transaction_datetime=txn.transaction_datetime.isoformat() if txn.transaction_datetime else None,
                    memo=memo,
                    deposit_amount=deposit,
                    matched_member_id=str(best_member.id),
                    matched_member_name=best_member.name,
                    payment_record_id=str(best_record.id),
                    required_amount=required,
                    amount_difference=0,
                    match_status="auto_match_candidate",
                    score=round(best_score, 2),
                    reason=f"이름+금액 정확 매칭: {best_member.name} {required:,}원",
                ))
            else:
                rows.append(ActivityFeeMatchRow(
                    transaction_id=str(txn.id),
                    transaction_datetime=txn.transaction_datetime.isoformat() if txn.transaction_datetime else None,
                    memo=memo,
                    deposit_amount=deposit,
                    matched_member_id=str(best_member.id),
                    matched_member_name=best_member.name,
                    payment_record_id=str(best_record.id),
                    required_amount=required,
                    amount_difference=deposit - required,
                    match_status="amount_mismatch",
                    score=round(best_score, 2),
                    reason=f"금액 불일치: 필요 {required:,}원 / 입금 {deposit:,}원",
                ))
        else:
            # No name match — try exact amount match for name_check_required
            exact_amount_records = [
                rec for rec in fee_records
                if rec.member_id and int(rec.required_amount or 0) == deposit
                and rec.status not in ("paid", "exempt")
            ]
            if exact_amount_records:
                candidate_rec = exact_amount_records[0]
                candidate_member = member_map.get(candidate_rec.member_id) if candidate_rec.member_id else None
                rows.append(ActivityFeeMatchRow(
                    transaction_id=str(txn.id),
                    transaction_datetime=txn.transaction_datetime.isoformat() if txn.transaction_datetime else None,
                    memo=memo,
                    deposit_amount=deposit,
                    matched_member_id=str(candidate_member.id) if candidate_member else None,
                    matched_member_name=candidate_member.name if candidate_member else None,
                    payment_record_id=str(candidate_rec.id),
                    required_amount=int(candidate_rec.required_amount or 0),
                    amount_difference=0,
                    match_status="name_check_required",
                    score=0.5,
                    reason="금액 일치하나 이름 확인 필요",
                ))
            else:
                # Truly unmatched
                rows.append(ActivityFeeMatchRow(
                    transaction_id=str(txn.id),
                    transaction_datetime=txn.transaction_datetime.isoformat() if txn.transaction_datetime else None,
                    memo=memo,
                    deposit_amount=deposit,
                    matched_member_id=None,
                    matched_member_name=None,
                    payment_record_id=None,
                    required_amount=None,
                    amount_difference=None,
                    match_status="unmatched",
                    score=None,
                    reason="매칭 후보 없음",
                ))

    # Compute summary
    summary = ActivityFeeMatchSummary(
        activity_id=str(activity_id),
        period=period_key,
        total_transactions=len(rows),
        auto_match_candidates=sum(1 for r in rows if r.match_status == "auto_match_candidate"),
        amount_mismatch=sum(1 for r in rows if r.match_status == "amount_mismatch"),
        name_check_required=sum(1 for r in rows if r.match_status == "name_check_required"),
        already_paid=sum(1 for r in rows if r.match_status == "already_paid"),
        already_matched=sum(1 for r in rows if r.match_status == "already_matched"),
        unmatched=sum(1 for r in rows if r.match_status == "unmatched"),
        excluded_transactions=excluded_count,
    )

    # Build rows payload for proposal
    rows_payload = [
        {
            "transaction_id": r.transaction_id,
            "payment_record_id": r.payment_record_id,
            "matched_member_id": r.matched_member_id,
            "deposit_amount": r.deposit_amount,
            "required_amount": r.required_amount,
            "match_status": r.match_status,
        }
        for r in rows
    ]

    proposal = create_action_proposal(
        db,
        action_type="activity_fee_transaction_match",
        source="activity_detail",
        activity_id=activity_id,
        payload={
            "activity_id": str(activity_id),
            "rows": rows_payload,
        },
        preview={
            "activity_id": str(activity_id),
            "activity_title": report.title,
            "period": period_key,
            "auto_match_candidates": summary.auto_match_candidates,
            "amount_mismatch": summary.amount_mismatch,
            "name_check_required": summary.name_check_required,
        },
        confidence=0.9,
        risk_level="low",
    )

    return ActivityFeeMatchPreviewResult(
        activity_id=str(activity_id),
        summary=summary,
        rows=rows,
        action_id=str(proposal.id),
        requires_confirmation=True,
        auto_apply=False,
    )


# ---------------------------------------------------------------------------
# Confirm
# ---------------------------------------------------------------------------

def confirm_activity_fee_transaction_matching(
    db: Session,
    action_id: UUID,
    confirmed_row_ids: list[str] | None = None,
) -> ActivityFeeMatchConfirmResult:
    """Apply matched transactions.

    confirmed_row_ids: if provided, only apply rows with these transaction_ids.
    If None, applies all auto_match_candidate rows.
    """
    from app.models.activity import ActivityReport
    from app.models import BankTransaction, PaymentRecord
    from app.models.assistant_action import AssistantActionProposal

    proposal = db.get(AssistantActionProposal, action_id)
    if not proposal:
        raise ValueError(f"Action proposal not found: {action_id}")
    if proposal.status != "pending":
        raise ValueError(f"Action proposal is not pending: {proposal.status}")

    payload = proposal.payload_json
    activity_id = UUID(str(payload["activity_id"]))
    rows_data: list[dict] = payload.get("rows", [])

    period_key = f"act-{str(activity_id)[:8]}"

    report = db.get(ActivityReport, activity_id)
    if not report:
        raise ValueError(f"활동을 찾을 수 없습니다: {activity_id}")

    matched_count = 0
    skipped_count = 0

    for row in rows_data:
        match_status = row.get("match_status", "")

        # Only apply auto_match_candidate (or user-confirmed name_check_required)
        should_apply = match_status == "auto_match_candidate"
        if confirmed_row_ids is not None:
            should_apply = row.get("transaction_id") in confirmed_row_ids

        if not should_apply:
            skipped_count += 1
            continue

        tx_id_str = row.get("transaction_id")
        pr_id_str = row.get("payment_record_id")
        deposit = row.get("deposit_amount", 0)
        required = row.get("required_amount")

        if not tx_id_str or not pr_id_str:
            skipped_count += 1
            continue

        try:
            tx_id = UUID(tx_id_str)
            pr_id = UUID(pr_id_str)
        except (ValueError, TypeError):
            skipped_count += 1
            continue

        # Revalidate
        txn = db.get(BankTransaction, tx_id)
        rec = db.get(PaymentRecord, pr_id)

        if not txn or not rec:
            skipped_count += 1
            continue

        # Scope check: activity_id must match
        if rec.period != period_key:
            skipped_count += 1
            continue

        # payment_type check
        if rec.payment_type != "activity_fee":
            skipped_count += 1
            continue

        # Already paid
        if rec.status in ("paid", "exempt"):
            skipped_count += 1
            continue

        # Transaction already matched
        if txn.match_status == "matched":
            skipped_count += 1
            continue

        # Exact amount check
        tx_deposit = int(txn.deposit_amount or 0)
        rec_required = int(rec.required_amount or 0)
        if tx_deposit != rec_required:
            skipped_count += 1
            continue

        # Apply
        rec.paid_amount = tx_deposit
        rec.status = "paid"
        rec.transaction_id = txn.id

        txn.match_status = "matched"
        txn.matched_member_id = rec.member_id
        txn.payment_type = "activity_fee"

        matched_count += 1

    # Mark proposal as applied
    proposal.status = "applied"
    proposal.confirmed_at = datetime.now(timezone.utc)
    proposal.applied_at = datetime.now(timezone.utc)
    proposal.preview_json = {
        **(proposal.preview_json or {}),
        "applied_result": {
            "matched_count": matched_count,
            "skipped_count": skipped_count,
        },
    }

    db.commit()

    return ActivityFeeMatchConfirmResult(
        ok=True,
        activity_id=str(activity_id),
        matched_count=matched_count,
        skipped_count=skipped_count,
        updated_payment_records=matched_count,
        updated_transactions=matched_count,
    )


def cancel_activity_fee_transaction_matching(db: Session, action_id: UUID) -> None:
    """Cancel a pending activity fee transaction matching proposal."""
    from app.models.assistant_action import AssistantActionProposal

    proposal = db.get(AssistantActionProposal, action_id)
    if not proposal:
        raise ValueError(f"Action proposal not found: {action_id}")
    if proposal.status != "pending":
        raise ValueError(f"Action proposal is not pending: {proposal.status}")
    proposal.status = "cancelled"
    proposal.cancelled_at = datetime.now(timezone.utc)
    db.commit()


# ---------------------------------------------------------------------------
# Apply handler (for assistant_action_service)
# ---------------------------------------------------------------------------

def apply_activity_fee_transaction_match_action(db: Session, payload: dict) -> dict:
    """Used by assistant_action_service to apply via action_id."""
    action_id = UUID(str(payload["action_id"]))
    confirmed_row_ids = payload.get("confirmed_row_ids")
    result = confirm_activity_fee_transaction_matching(
        db=db,
        action_id=action_id,
        confirmed_row_ids=confirmed_row_ids,
    )
    return {
        "ok": result.ok,
        "activity_id": result.activity_id,
        "matched_count": result.matched_count,
        "skipped_count": result.skipped_count,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _fuzzy_name_score(name: str, text: str) -> float:
    """Simple fuzzy match: returns ratio of characters matched."""
    if not name or not text:
        return 0.0
    name = name.strip()
    if len(name) < 2:
        return 0.0
    matched = sum(1 for ch in name if ch in text)
    return matched / len(name)
