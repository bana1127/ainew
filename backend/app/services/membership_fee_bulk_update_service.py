"""Membership fee bulk update service (Task 37).

Supports preview + confirm operations on multiple membership_fee PaymentRecords.

Scope safety:
  - Only payment_type="membership_fee" records are accepted
  - activity_fee records are rejected (individual or mixed batches)
  - Records must exist and match the requested period
  - No DB changes in preview mode

Operations:
  - mark_paid      : paid_amount = required_amount, status = paid (exempt if req=0)
  - mark_unpaid    : paid_amount = 0, status = unpaid
  - mark_need_check: status = need_check (keep paid_amount)
  - mark_exempt    : required_amount = 0, paid_amount = 0, status = exempt
  - set_paid_amount: paid_amount = value, recalculate status
  - recalculate_required_amount: recalculate required_amount from policy
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.orm import Session


VALID_OPERATIONS = {
    "mark_paid",
    "mark_unpaid",
    "mark_need_check",
    "mark_exempt",
    "set_paid_amount",
    "recalculate_required_amount",
}

STATUS_LABEL = {
    "unpaid": "미납",
    "partial": "부분 납부",
    "paid": "납부 완료",
    "overpaid": "초과 납부",
    "need_check": "확인 필요",
    "exempt": "면제",
}


def _recalc_status(paid: int, required: int) -> str:
    if required <= 0:
        return "exempt"
    if paid == 0:
        return "unpaid"
    if paid < required:
        return "partial"
    if paid == required:
        return "paid"
    return "overpaid"


@dataclass
class BulkUpdateRow:
    payment_record_id: str
    member_id: str | None
    member_name: str | None
    student_id: str | None
    before_required_amount: int
    before_paid_amount: int
    before_status: str
    after_required_amount: int
    after_paid_amount: int
    after_status: str
    will_change: bool
    note: str | None = None


@dataclass
class BulkUpdateSummary:
    selected: int
    will_change: int
    no_change: int
    will_be_paid: int = 0
    will_be_exempt: int = 0
    will_be_unpaid: int = 0
    will_be_need_check: int = 0
    danger: bool = False
    danger_reason: str | None = None


@dataclass
class BulkUpdatePreviewResult:
    ok: bool
    requires_confirmation: bool
    auto_apply: bool
    action_id: str
    operation: str
    period: str
    summary: BulkUpdateSummary
    rows: list[BulkUpdateRow]


@dataclass
class BulkUpdateConfirmResult:
    ok: bool
    operation: str
    period: str
    updated_count: int
    skipped_count: int
    rows_updated: list[str]


def preview_bulk_update(
    db: Session,
    period: str,
    payment_record_ids: list[str],
    operation: str,
    paid_amount_value: int | None = None,
) -> BulkUpdatePreviewResult:
    """Compute a preview of what would change. Never modifies the DB."""
    from app.models import Member, PaymentRecord
    from app.services.assistant_action_service import create_action_proposal

    if operation not in VALID_OPERATIONS:
        raise ValueError(f"Unknown operation: {operation}. Valid: {VALID_OPERATIONS}")
    if not payment_record_ids:
        raise ValueError("No payment_record_ids provided")

    uuids = [UUID(rid) for rid in payment_record_ids]
    if len(set(uuids)) != len(uuids):
        raise ValueError("Duplicate payment_record_ids are not allowed")

    records = list(db.scalars(
        select(PaymentRecord).where(PaymentRecord.id.in_(uuids))
    ))
    records_by_id = {r.id: r for r in records}
    missing_ids = [str(rid) for rid in uuids if rid not in records_by_id]
    if missing_ids:
        raise ValueError(f"PaymentRecord not found: {', '.join(missing_ids)}")

    member_ids = {r.member_id for r in records if r.member_id}
    member_map: dict[UUID, Member] = {}
    if member_ids:
        for m in db.scalars(select(Member).where(Member.id.in_(member_ids))):
            member_map[m.id] = m

    rows: list[BulkUpdateRow] = []
    danger = False
    danger_reason = None

    for rid in uuids:
        rec = records_by_id[rid]
        # Scope check: must be membership_fee
        if rec.payment_type != "membership_fee":
            raise ValueError(
                f"Record {rec.id} has payment_type={rec.payment_type!r}. "
                "Only membership_fee records can be bulk-updated."
            )
        if rec.period != period:
            raise ValueError(
                f"Record {rec.id} has period={rec.period!r}, expected {period!r}."
            )

        member = member_map.get(rec.member_id) if rec.member_id else None
        before_req = int(rec.required_amount or 0)
        before_paid = int(rec.paid_amount or 0)
        before_status = rec.status or "unpaid"

        after_req = before_req
        after_paid = before_paid
        after_status = before_status
        note = None

        if operation == "mark_paid":
            if before_req <= 0:
                after_paid = 0
                after_status = "exempt"
                note = "required_amount=0 → 면제 처리"
            else:
                after_paid = before_req
                after_status = "paid"
        elif operation == "mark_unpaid":
            after_paid = 0
            after_status = _recalc_status(0, after_req)
            if before_status in ("exempt",):
                note = "required_amount=0 대상은 exempt로 유지됩니다."
        elif operation == "mark_need_check":
            after_status = "need_check"
        elif operation == "mark_exempt":
            after_req = 0
            after_paid = 0
            after_status = "exempt"
            danger = True
            danger_reason = "면제 처리는 required_amount를 0으로 초기화합니다."
        elif operation == "set_paid_amount":
            if paid_amount_value is None:
                raise ValueError("set_paid_amount operation requires paid_amount_value")
            after_paid = max(0, paid_amount_value)
            after_status = _recalc_status(after_paid, after_req)
        elif operation == "recalculate_required_amount":
            from app.services.membership_fee_policy import decide_membership_fee, resolve_current_term

            if member is None:
                raise ValueError(f"Member not found for record {rec.id}")
            decision = decide_membership_fee(
                member,
                current_term=resolve_current_term(db, period),
                existing_record=rec,
            )
            after_req = decision.required_amount
            after_status = _recalc_status(after_paid, after_req)
            note = decision.fee_rule_reason

        will_change = (
            after_req != before_req
            or after_paid != before_paid
            or after_status != before_status
        )

        rows.append(BulkUpdateRow(
            payment_record_id=str(rec.id),
            member_id=str(rec.member_id) if rec.member_id else None,
            member_name=member.name if member else None,
            student_id=member.student_id if member else None,
            before_required_amount=before_req,
            before_paid_amount=before_paid,
            before_status=before_status,
            after_required_amount=after_req,
            after_paid_amount=after_paid,
            after_status=after_status,
            will_change=will_change,
            note=note,
        ))

    # Build summary
    will_change_count = sum(1 for r in rows if r.will_change)
    summary = BulkUpdateSummary(
        selected=len(rows),
        will_change=will_change_count,
        no_change=len(rows) - will_change_count,
        will_be_paid=sum(1 for r in rows if r.after_status == "paid" and r.will_change),
        will_be_exempt=sum(1 for r in rows if r.after_status == "exempt" and r.will_change),
        will_be_unpaid=sum(1 for r in rows if r.after_status == "unpaid" and r.will_change),
        will_be_need_check=sum(1 for r in rows if r.after_status == "need_check" and r.will_change),
        danger=danger,
        danger_reason=danger_reason,
    )

    # Create proposal
    proposal = create_action_proposal(
        db,
        action_type="membership_fee_bulk_update",
        source="payments",
        activity_id=None,
        payload={
            "period": period,
            "operation": operation,
            "payment_record_ids": payment_record_ids,
            "paid_amount_value": paid_amount_value,
        },
        preview={
            "period": period,
            "operation": operation,
            "selected": summary.selected,
            "will_change": summary.will_change,
        },
        confidence=0.95,
        risk_level="high" if danger else "medium",
    )

    return BulkUpdatePreviewResult(
        ok=True,
        requires_confirmation=True,
        auto_apply=False,
        action_id=str(proposal.id),
        operation=operation,
        period=period,
        summary=summary,
        rows=rows,
    )


def confirm_bulk_update(
    db: Session,
    action_id: UUID,
) -> BulkUpdateConfirmResult:
    """Apply the bulk update proposal."""
    from app.models import Member, PaymentRecord
    from app.models.assistant_action import AssistantActionProposal

    proposal = db.get(AssistantActionProposal, action_id)
    if not proposal:
        raise ValueError(f"Action proposal not found: {action_id}")
    if proposal.status != "pending":
        raise ValueError(f"Action proposal is not pending: {proposal.status}")

    payload = proposal.payload_json
    period = payload["period"]
    operation = payload["operation"]
    payment_record_ids = payload["payment_record_ids"]
    paid_amount_value = payload.get("paid_amount_value")

    if operation not in VALID_OPERATIONS:
        raise ValueError(f"Unknown operation: {operation}. Valid: {VALID_OPERATIONS}")
    if operation == "set_paid_amount" and paid_amount_value is None:
        raise ValueError("set_paid_amount operation requires paid_amount_value")

    uuids = [UUID(rid) for rid in payment_record_ids]
    records = list(db.scalars(
        select(PaymentRecord).where(PaymentRecord.id.in_(uuids))
    ))
    records_by_id = {r.id: r for r in records}

    updated_ids: list[str] = []
    skipped = len([rid for rid in uuids if rid not in records_by_id])

    try:
        from app.models import PaymentAdjustmentLog
    except ImportError:  # pragma: no cover - used only by lightweight test doubles
        PaymentAdjustmentLog = None  # type: ignore[assignment]

    for rid in uuids:
        rec = records_by_id.get(rid)
        if rec is None:
            continue
        if rec.payment_type != "membership_fee":
            raise ValueError(
                f"Record {rec.id} has payment_type={rec.payment_type!r}. "
                "Only membership_fee records can be bulk-updated."
            )
        if rec.period != period:
            raise ValueError(f"Record {rec.id} has period={rec.period!r}, expected {period!r}.")

    for rid in uuids:
        rec = records_by_id.get(rid)
        if rec is None:
            continue

        before_req = int(rec.required_amount or 0)
        before_paid = int(rec.paid_amount or 0)
        before_status = rec.status

        if operation == "mark_paid":
            if before_req <= 0:
                rec.paid_amount = 0
                rec.status = "exempt"
            else:
                rec.paid_amount = before_req
                rec.status = "paid"
        elif operation == "mark_unpaid":
            rec.paid_amount = 0
            rec.status = _recalc_status(0, int(rec.required_amount or 0))
        elif operation == "mark_need_check":
            rec.status = "need_check"
        elif operation == "mark_exempt":
            rec.required_amount = 0
            rec.paid_amount = 0
            rec.status = "exempt"
        elif operation == "set_paid_amount":
            if paid_amount_value is not None:
                new_paid = max(0, int(paid_amount_value))
                rec.paid_amount = new_paid
                rec.status = _recalc_status(new_paid, before_req)
        elif operation == "recalculate_required_amount":
            from app.services.membership_fee_policy import decide_membership_fee, resolve_current_term

            member = db.get(Member, rec.member_id)
            if member is None:
                raise ValueError(f"Member not found for record {rec.id}")
            decision = decide_membership_fee(
                member,
                current_term=resolve_current_term(db, period),
                existing_record=rec,
            )
            rec.required_amount = decision.required_amount
            rec.status = _recalc_status(int(rec.paid_amount or 0), int(rec.required_amount or 0))
            rec.fee_tier = decision.fee_tier
            rec.fee_rule_reason = decision.fee_rule_reason
            rec.joined_term = decision.joined_term
            rec.current_term = decision.current_term

        if getattr(rec, "transaction_id", None) is None:
            rec.payment_source = "manual"

        if PaymentAdjustmentLog is not None and hasattr(db, "add"):
            db.add(
                PaymentAdjustmentLog(
                    payment_record_id=rec.id,
                    transaction_id=getattr(rec, "transaction_id", None),
                    action=f"membership_fee_bulk_update:{operation}",
                    previous_status=before_status,
                    new_status=rec.status,
                    previous_paid_amount=before_paid,
                    new_paid_amount=int(rec.paid_amount or 0),
                    reason=None,
                    metadata_json={
                        "before_required_amount": before_req,
                        "after_required_amount": int(rec.required_amount or 0),
                        "payment_source": getattr(rec, "payment_source", None),
                    },
                )
            )

        updated_ids.append(str(rec.id))

    proposal.status = "applied"
    proposal.confirmed_at = datetime.now(timezone.utc)
    proposal.applied_at = datetime.now(timezone.utc)
    proposal.preview_json = {
        **(proposal.preview_json or {}),
        "applied_result": {"updated": len(updated_ids), "skipped": skipped},
    }

    db.commit()

    return BulkUpdateConfirmResult(
        ok=True,
        operation=operation,
        period=period,
        updated_count=len(updated_ids),
        skipped_count=skipped,
        rows_updated=updated_ids,
    )
