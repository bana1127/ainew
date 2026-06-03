from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.services.budget_service import (
    _date_value,
    _in_range,
    _to_int,
    _val,
    compute_budget_vs_actual,
    evidence_target_url,
    target_url_for_payment_record,
)


def build_review_items(
    *,
    payment_records: list[Any],
    transactions: list[Any],
    receipts: list[Any],
    budget_rows: list[dict[str, Any]],
    period: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []

    # ── Membership fee: aggregate as a single summary item (NOT individual rows) ──
    membership_unpaid_count = 0
    membership_unpaid_amount = 0
    # ── Activity fee: aggregate by activity ──
    activity_unpaid_by_activity: dict[str, dict[str, Any]] = {}

    for record in payment_records:
        if period and str(_val(record, "period", "")) != period:
            continue
        payment_type = str(_val(record, "payment_type", ""))
        status = str(_val(record, "status", ""))
        if payment_type not in {"membership_fee", "activity_fee"} or status not in {"unpaid", "partial", "need_check"}:
            continue
        due = max(0, _to_int(_val(record, "required_amount")) - _to_int(_val(record, "paid_amount")))
        if due <= 0 and status != "need_check":
            continue

        if payment_type == "membership_fee":
            # Aggregate — do NOT add as individual row
            membership_unpaid_count += 1
            membership_unpaid_amount += due
        else:
            # activity_fee: aggregate per activity
            activity_id = str(_val(record, "activity_report_id") or "unknown")
            if activity_id not in activity_unpaid_by_activity:
                activity_unpaid_by_activity[activity_id] = {
                    "activity_id": activity_id,
                    "count": 0,
                    "amount": 0,
                    "target_url": target_url_for_payment_record(record),
                }
            activity_unpaid_by_activity[activity_id]["count"] += 1
            activity_unpaid_by_activity[activity_id]["amount"] += due

    # ── Emit membership fee summary (one item, not per-member rows) ──
    if membership_unpaid_count > 0:
        items.append({
            "id": "membership_fee_summary",
            "type": "membership_fee_summary",
            "label": "회비 미납",
            "title": f"{membership_unpaid_count}명 미납 · {membership_unpaid_amount:,}원",
            "amount": membership_unpaid_amount,
            "status": "unpaid",
            "target_url": "/payments",
            "severity": "warning",
            "source_id": "membership_fee_summary",
        })

    # ── Emit activity fee summary per activity ──
    for act_data in activity_unpaid_by_activity.values():
        items.append({
            "id": f"activity_fee_summary:{act_data['activity_id']}",
            "type": "activity_fee_summary",
            "label": "활동비 미납",
            "title": f"{act_data['count']}명 미납 · {act_data['amount']:,}원",
            "amount": act_data["amount"],
            "status": "unpaid",
            "target_url": act_data["target_url"],
            "severity": "warning",
            "source_id": act_data["activity_id"],
        })

    for tx in transactions:
        if not _in_range(_val(tx, "transaction_datetime"), start_date, end_date):
            continue
        if str(_val(tx, "review_status", "open")) == "resolved":
            continue
        tx_id = str(_val(tx, "id"))
        amount = _to_int(_val(tx, "deposit_amount")) or _to_int(_val(tx, "withdraw_amount"))
        if not _val(tx, "payment_type"):
            items.append({
                "id": f"unclassified_transaction:{tx_id}",
                "type": "unclassified_transaction",
                "label": "미분류 거래",
                "title": _val(tx, "memo") or "거래내역",
                "amount": amount,
                "status": _val(tx, "match_status"),
                "target_url": "/transactions",
                "severity": "warning",
                "source_id": tx_id,
            })
        if str(_val(tx, "match_status", "")) in {"unmatched", "need_check", "amount_mismatch", "duplicate_candidate"}:
            items.append({
                "id": f"transaction_review:{tx_id}",
                "type": str(_val(tx, "match_status", "transaction_review")),
                "label": "확인 필요 거래" if str(_val(tx, "match_status", "")) != "amount_mismatch" else "금액 불일치 거래",
                "title": _val(tx, "memo") or "거래내역",
                "amount": amount,
                "status": _val(tx, "match_status"),
                "target_url": "/transactions",
                "severity": "warning",
                "source_id": tx_id,
            })
        if _to_int(_val(tx, "withdraw_amount")) > 0 and not _val(tx, "linked_activity_id") and str(_val(tx, "payment_type", "")) != "refund":
            items.append({
                "id": f"missing_evidence_transaction:{tx_id}",
                "type": "missing_evidence",
                "label": "증빙 없는 지출",
                "title": _val(tx, "memo") or "출금 거래",
                "amount": _to_int(_val(tx, "withdraw_amount")),
                "status": _val(tx, "review_status", "open"),
                "target_url": "/transactions",
                "severity": "danger",
                "source_id": tx_id,
            })

    for receipt in receipts:
        if not _in_range(_val(receipt, "receipt_date"), start_date, end_date):
            continue
        receipt_status = str(_val(receipt, "evidence_status", "pending"))
        if receipt_status not in {"missing", "pending", "need_check"} and _val(receipt, "file_id") is not None:
            continue
        activity_id = _val(receipt, "activity_report_id")
        items.append({
            "id": f"missing_evidence_receipt:{_val(receipt, 'id')}",
            "type": "missing_evidence",
            "label": "증빙 없는 지출",
            "title": _val(receipt, "store_name") or "영수증",
            "amount": _to_int(_val(receipt, "amount")),
            "status": receipt_status,
            "target_url": evidence_target_url(activity_id),
            "severity": "danger",
            "source_id": str(_val(receipt, "id")),
        })

    for record in payment_records:
        if str(_val(record, "refund_status", "")) not in {"refund_needed", "refund_required", "refund_pending"}:
            continue
        items.append({
            "id": f"refund_needed:{_val(record, 'id')}",
            "type": "refund_needed",
            "label": "환불 필요",
            "title": _val(record, "member_name") or _val(record, "member_id"),
            "amount": _to_int(_val(record, "refund_amount")),
            "status": _val(record, "refund_status"),
            "target_url": target_url_for_payment_record(record),
            "severity": "danger",
            "source_id": str(_val(record, "id")),
        })

    for row in budget_rows:
        if not row.get("over_budget"):
            continue
        items.append({
            "id": f"budget_overrun:{row['category_id']}",
            "type": "budget_overrun",
            "label": "예산 초과 항목",
            "title": row["category_name"],
            "amount": row["difference_amount"],
            "status": "over_budget",
            "target_url": "/budget",
            "severity": "danger",
            "source_id": row["category_id"],
        })

    return items


def get_review_items(
    db: Session,
    *,
    period: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict[str, Any]]:
    from app.models import BankTransaction, BudgetCategory, BudgetPlan, PaymentRecord, Receipt

    payment_records = list(db.scalars(select(PaymentRecord)))
    transactions = list(db.scalars(select(BankTransaction)))
    receipts = list(db.scalars(select(Receipt)))
    categories = list(db.scalars(select(BudgetCategory)))
    plans = list(db.scalars(select(BudgetPlan)))
    budget_rows = compute_budget_vs_actual(
        categories,
        plans,
        transactions,
        period=period or "",
        start_date=start_date,
        end_date=end_date,
    )
    return build_review_items(
        payment_records=payment_records,
        transactions=transactions,
        receipts=receipts,
        budget_rows=budget_rows,
        period=period,
        start_date=start_date,
        end_date=end_date,
    )


def preview_transaction_classification(
    db: Session,
    *,
    transaction_id: UUID,
    payload: dict[str, Any],
) -> dict[str, Any]:
    from app.models import BankTransaction
    from app.services.assistant_action_service import create_action_proposal

    tx = db.get(BankTransaction, transaction_id)
    if tx is None:
        raise ValueError("Transaction not found")

    before = {
        "payment_type": tx.payment_type,
        "budget_category_id": str(tx.budget_category_id) if tx.budget_category_id else None,
        "linked_activity_id": str(tx.linked_activity_id) if tx.linked_activity_id else None,
        "match_status": tx.match_status,
        "review_status": tx.review_status,
        "review_note": tx.review_note,
    }
    after = {**before}
    for key in ("payment_type", "budget_category_id", "linked_activity_id", "match_status", "review_status", "review_note"):
        if key in payload:
            value = payload[key]
            after[key] = str(value) if isinstance(value, UUID) else value

    proposal = create_action_proposal(
        db,
        action_type="budget_transaction_classify",
        source="budget",
        activity_id=UUID(str(after["linked_activity_id"])) if after.get("linked_activity_id") else None,
        payload={
            "transaction_id": str(transaction_id),
            **after,
        },
        preview={"before": before, "after": after},
        confidence=0.9,
        risk_level="medium",
    )
    return {
        "ok": True,
        "requires_confirmation": True,
        "auto_apply": False,
        "action_id": str(proposal.id),
        "transaction_id": str(transaction_id),
        "before": before,
        "after": after,
    }


def confirm_transaction_classification(db: Session, *, action_id: UUID) -> dict[str, Any]:
    from app.models import BankTransaction
    from app.models.assistant_action import AssistantActionProposal

    proposal = db.get(AssistantActionProposal, action_id)
    if proposal is None:
        raise ValueError("Action proposal not found")
    if proposal.status != "pending":
        raise ValueError(f"Action proposal is not pending: {proposal.status}")

    payload = proposal.payload_json or {}
    tx = db.get(BankTransaction, UUID(str(payload["transaction_id"])))
    if tx is None:
        raise ValueError("Transaction not found")

    tx.payment_type = payload.get("payment_type")
    tx.budget_category_id = UUID(str(payload["budget_category_id"])) if payload.get("budget_category_id") else None
    tx.linked_activity_id = UUID(str(payload["linked_activity_id"])) if payload.get("linked_activity_id") else None
    tx.match_status = payload.get("match_status") or tx.match_status
    tx.review_status = payload.get("review_status") or tx.review_status
    tx.review_note = payload.get("review_note")

    proposal.status = "applied"
    if proposal.confirmed_at is None:
        proposal.confirmed_at = datetime.now(timezone.utc)
    proposal.applied_at = datetime.now(timezone.utc)
    proposal.preview_json = {
        **(proposal.preview_json or {}),
        "applied_result": {"transaction_id": str(tx.id), "review_status": tx.review_status},
    }
    db.commit()
    db.refresh(tx)
    return {
        "ok": True,
        "transaction_id": str(tx.id),
        "payment_type": tx.payment_type,
        "budget_category_id": str(tx.budget_category_id) if tx.budget_category_id else None,
        "linked_activity_id": str(tx.linked_activity_id) if tx.linked_activity_id else None,
        "match_status": tx.match_status,
        "review_status": tx.review_status,
        "review_note": tx.review_note,
    }


def resolve_review_item(db: Session, *, item_id: str, note: str | None = None) -> dict[str, Any]:
    from app.models import BankTransaction

    if ":" not in item_id:
        raise ValueError("Invalid review item id")
    item_type, source_id = item_id.split(":", 1)
    if item_type in {"unclassified_transaction", "transaction_review", "missing_evidence_transaction"}:
        tx = db.get(BankTransaction, UUID(source_id))
        if tx is None:
            raise ValueError("Transaction not found")
        tx.review_status = "resolved"
        if note:
            tx.review_note = note
        db.commit()
        return {"ok": True, "id": item_id, "status": "resolved"}
    raise ValueError("This review item must be resolved from its target page")
