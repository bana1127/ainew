from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from types import SimpleNamespace
from typing import Any
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.services.quarter_service import (
    get_operating_quarter,
    parse_operating_quarter,
    quarter_date_range_from_str,
)


DEFAULT_BUDGET_CATEGORIES: list[tuple[str, str, int]] = [
    ("회비", "income", 10),
    ("활동비", "income", 20),
    ("학교 지원금", "income", 30),
    ("기타 수입", "income", 90),
    ("재료비", "expense", 10),
    ("대관비", "expense", 20),
    ("식비", "expense", 30),
    ("홍보비", "expense", 40),
    ("비품비", "expense", 50),
    ("환불", "expense", 60),
    ("기타 지출", "expense", 90),
]

INACTIVE_PARTICIPANT_STATUSES = {"removed", "cancelled", "excluded", "deleted", "inactive"}
INACTIVE_ACTIVITY_FEE_STATUSES = {"cancelled", "excluded"}


def _val(obj: Any, name: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _to_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _date_value(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _in_range(value: Any, start_date: date | None, end_date: date | None) -> bool:
    d = _date_value(value)
    if d is None:
        return True
    if start_date and d < start_date:
        return False
    if end_date and d > end_date:
        return False
    return True


def _period_matches(record: Any, period: str | None) -> bool:
    return period is None or str(_val(record, "period", "")) == period


def _is_active_participant(participant: Any) -> bool:
    return str(_val(participant, "status", "") or "active") not in INACTIVE_PARTICIPANT_STATUSES


def _is_active_activity_fee_record(record: Any) -> bool:
    return str(_val(record, "status", "") or "") not in INACTIVE_ACTIVITY_FEE_STATUSES


def parse_date_filter(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)


def target_url_for_payment_record(record: Any) -> str:
    payment_type = str(_val(record, "payment_type", ""))
    if payment_type == "activity_fee":
        activity_id = _val(record, "activity_report_id")
        if activity_id:
            return f"/activities/{activity_id}?tab=activity-fee"
        return "/activities?filter=activity-fee-unpaid"
    return "/payments"


def evidence_target_url(activity_id: Any | None) -> str:
    if activity_id:
        return f"/activities/{activity_id}?tab=evidence"
    return "/transactions"


def _is_budget_excluded(transaction: Any) -> bool:
    """Return True if transaction is excluded from all budget aggregation."""
    return bool(_val(transaction, "exclude_from_budget", False))


def _is_income_excluded(transaction: Any) -> bool:
    return bool(_val(transaction, "exclude_from_budget", False)) or bool(
        _val(transaction, "exclude_from_income", False)
    )


def _is_expense_excluded(transaction: Any) -> bool:
    return bool(_val(transaction, "exclude_from_budget", False)) or bool(
        _val(transaction, "exclude_from_expense", False)
    )


def compute_finance_summary(
    transactions: list[Any],
    payment_records: list[Any],
    receipts: list[Any],
    *,
    period: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    operating_quarter: str | None = None,
) -> dict[str, Any]:
    # Apply operating_quarter as date range override
    if operating_quarter:
        q_start, q_end = quarter_date_range_from_str(operating_quarter)
        start_date = q_start
        end_date = q_end

    txs = [
        t for t in transactions
        if _in_range(_val(t, "transaction_datetime"), start_date, end_date)
    ]
    records = [r for r in payment_records if _period_matches(r, period)]

    # Income: deposit transactions not excluded from income
    income_txs = [t for t in txs if not _is_income_excluded(t)]
    # Expense: withdraw transactions not excluded from expense
    expense_txs = [t for t in txs if not _is_expense_excluded(t)]

    total_income = sum(_to_int(_val(t, "deposit_amount")) for t in income_txs)
    total_expense = sum(_to_int(_val(t, "withdraw_amount")) for t in expense_txs)

    # Membership fee income (deposit transactions with payment_type=membership_fee)
    membership_fee_income = sum(
        _to_int(_val(t, "deposit_amount"))
        for t in income_txs
        if str(_val(t, "payment_type", "") or "") == "membership_fee"
    )
    # Activity fee income
    activity_fee_income = sum(
        _to_int(_val(t, "deposit_amount"))
        for t in income_txs
        if str(_val(t, "payment_type", "") or "") == "activity_fee"
    )
    # Other income
    other_income = total_income - membership_fee_income - activity_fee_income

    # Excluded transaction counts
    excluded_income_count = sum(
        1 for t in txs
        if _is_income_excluded(t) and _to_int(_val(t, "deposit_amount")) > 0
    )
    excluded_expense_count = sum(
        1 for t in txs
        if _is_expense_excluded(t) and _to_int(_val(t, "withdraw_amount")) > 0
    )
    excluded_income_amount = sum(
        _to_int(_val(t, "deposit_amount"))
        for t in txs
        if _is_income_excluded(t) and _to_int(_val(t, "deposit_amount")) > 0
    )
    excluded_expense_amount = sum(
        _to_int(_val(t, "withdraw_amount"))
        for t in txs
        if _is_expense_excluded(t) and _to_int(_val(t, "withdraw_amount")) > 0
    )

    balance_candidates = [
        t for t in txs
        if _val(t, "balance") is not None and _val(t, "transaction_datetime") is not None
    ]
    if balance_candidates:
        latest = max(balance_candidates, key=lambda t: _val(t, "transaction_datetime"))
        current_balance = _to_int(_val(latest, "balance"))
    else:
        current_balance = total_income - total_expense

    receivable_records = [
        r for r in records
        if str(_val(r, "payment_type", "")) in {"membership_fee", "activity_fee"}
        and str(_val(r, "status", "")) in {"unpaid", "partial", "need_check"}
    ]
    receivable_amount = sum(
        max(0, _to_int(_val(r, "required_amount")) - _to_int(_val(r, "paid_amount")))
        for r in receivable_records
    )
    refund_scheduled_amount = sum(
        _to_int(_val(r, "refund_amount")) or max(0, _to_int(_val(r, "paid_amount")) - _to_int(_val(r, "required_amount")))
        for r in records
        if str(_val(r, "refund_status", "")) in {"refund_needed", "refund_required", "refund_pending"}
    )
    review_transactions = [
        t for t in txs
        if str(_val(t, "review_status", "open")) != "resolved"
        and (
            str(_val(t, "match_status", "")) in {"unmatched", "need_check", "amount_mismatch", "duplicate_candidate"}
            or not _val(t, "payment_type")
        )
        and not _is_budget_excluded(t)
    ]
    missing_evidence_count = len([
        t for t in txs
        if _to_int(_val(t, "withdraw_amount")) > 0
        and not _val(t, "linked_activity_id")
        and str(_val(t, "payment_type", "")) not in {"refund", "transfer"}
        and str(_val(t, "review_status", "open")) != "resolved"
        and not _is_expense_excluded(t)
    ]) + len([
        r for r in receipts
        if str(_val(r, "evidence_status", "")) in {"missing", "pending", "need_check"}
        or _val(r, "file_id") is None
    ])

    # Receipt evidence breakdown
    receipts_in_range = [
        r for r in receipts
        if _in_range(_val(r, "receipt_date"), start_date, end_date)
    ]
    evidence_linked_expense = sum(
        _to_int(_val(r, "amount")) for r in receipts_in_range
        if _val(r, "activity_report_id") is not None
        and str(_val(r, "evidence_status", "")) not in {"missing", "pending"}
    )
    evidence_missing_expense = sum(
        _to_int(_val(t, "withdraw_amount")) for t in expense_txs
        if not _val(t, "linked_activity_id")
        and str(_val(t, "payment_type", "")) not in {"refund", "transfer"}
        and str(_val(t, "review_status", "open")) != "resolved"
    )

    return {
        "current_balance": current_balance,
        "total_income": total_income,
        "total_expense": total_expense,
        "net_change": total_income - total_expense,
        "receivable_amount": receivable_amount,
        "refund_scheduled_amount": refund_scheduled_amount,
        "review_transaction_count": len(review_transactions),
        "missing_evidence_count": missing_evidence_count,
        "period": period,
        "operating_quarter": operating_quarter,
        "start_date": start_date.isoformat() if start_date else None,
        "end_date": end_date.isoformat() if end_date else None,
        # Extended quarter summary fields
        "membership_fee_income": membership_fee_income,
        "activity_fee_income": activity_fee_income,
        "other_income": other_income,
        "evidence_linked_expense": evidence_linked_expense,
        "evidence_missing_expense": evidence_missing_expense,
        "excluded_income_count": excluded_income_count,
        "excluded_expense_count": excluded_expense_count,
        "excluded_income_amount": excluded_income_amount,
        "excluded_expense_amount": excluded_expense_amount,
    }


def compute_cashflow(
    transactions: list[Any],
    *,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict[str, Any]]:
    buckets: dict[str, dict[str, int]] = defaultdict(lambda: {"income": 0, "expense": 0})
    for tx in transactions:
        if not _in_range(_val(tx, "transaction_datetime"), start_date, end_date):
            continue
        d = _date_value(_val(tx, "transaction_datetime"))
        label = d.strftime("%Y-%m") if d else "날짜 없음"
        buckets[label]["income"] += _to_int(_val(tx, "deposit_amount"))
        buckets[label]["expense"] += _to_int(_val(tx, "withdraw_amount"))
    return [
        {
            "bucket": bucket,
            "income": values["income"],
            "expense": values["expense"],
            "net": values["income"] - values["expense"],
        }
        for bucket, values in sorted(buckets.items())
    ]


def _category_key(category: Any) -> tuple[str, str]:
    return (str(_val(category, "type", "")), str(_val(category, "name", "")))


def _fallback_category_name(transaction: Any) -> tuple[str, str]:
    payment_type = str(_val(transaction, "payment_type", "") or "")
    memo = str(_val(transaction, "memo", "") or "")
    if _to_int(_val(transaction, "deposit_amount")) > 0:
        if payment_type == "membership_fee":
            return ("income", "회비")
        if payment_type == "activity_fee":
            return ("income", "활동비")
        if "지원" in memo or "보조" in memo:
            return ("income", "학교 지원금")
        return ("income", "기타 수입")
    if payment_type in {"refund", "refund_fee"}:
        return ("expense", "환불")
    for keyword, name in [
        ("재료", "재료비"),
        ("대관", "대관비"),
        ("식", "식비"),
        ("홍보", "홍보비"),
        ("비품", "비품비"),
        ("환불", "환불"),
    ]:
        if keyword in memo:
            return ("expense", name)
    return ("expense", "기타 지출")


def compute_budget_vs_actual(
    categories: list[Any],
    plans: list[Any],
    transactions: list[Any],
    *,
    period: str,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict[str, Any]]:
    category_by_id = {str(_val(c, "id")): c for c in categories}
    category_by_key = {_category_key(c): c for c in categories}
    planned_by_category = {
        str(_val(p, "category_id")): _to_int(_val(p, "planned_amount"))
        for p in plans
        if str(_val(p, "period", "")) == period
    }
    notes_by_category = {
        str(_val(p, "category_id")): _val(p, "note")
        for p in plans
        if str(_val(p, "period", "")) == period
    }
    actual_by_category: dict[str, int] = defaultdict(int)
    for tx in transactions:
        if not _in_range(_val(tx, "transaction_datetime"), start_date, end_date):
            continue
        amount = _to_int(_val(tx, "deposit_amount")) or _to_int(_val(tx, "withdraw_amount"))
        if amount <= 0:
            continue
        explicit_id = _val(tx, "budget_category_id")
        category = category_by_id.get(str(explicit_id)) if explicit_id else None
        if category is None:
            category = category_by_key.get(_fallback_category_name(tx))
        if category is not None:
            actual_by_category[str(_val(category, "id"))] += amount

    rows: list[dict[str, Any]] = []
    for category in sorted(categories, key=lambda c: (_val(c, "type", ""), _to_int(_val(c, "sort_order")), _val(c, "name", ""))):
        category_id = str(_val(category, "id"))
        planned = planned_by_category.get(category_id, 0)
        actual = actual_by_category.get(category_id, 0)
        rows.append({
            "category_id": category_id,
            "category_name": _val(category, "name"),
            "type": _val(category, "type"),
            "is_active": bool(_val(category, "is_active", True)),
            "planned_amount": planned,
            "actual_amount": actual,
            "difference_amount": actual - planned,
            "over_budget": _val(category, "type") == "expense" and planned > 0 and actual > planned,
            "note": notes_by_category.get(category_id),
        })
    return rows


def compute_activity_settlements(
    activities: list[Any],
    participants: list[Any],
    payment_records: list[Any],
    receipts: list[Any],
    transactions: list[Any],
    *,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict[str, Any]]:
    participant_count: dict[str, int] = defaultdict(int)
    for p in participants:
        if not _is_active_participant(p):
            continue
        participant_count[str(_val(p, "activity_report_id"))] += 1

    fee_required: dict[str, int] = defaultdict(int)
    fee_paid: dict[str, int] = defaultdict(int)
    for r in payment_records:
        if str(_val(r, "payment_type", "")) != "activity_fee":
            continue
        if not _is_active_activity_fee_record(r):
            continue
        activity_id = _val(r, "activity_report_id")
        if activity_id:
            fee_required[str(activity_id)] += _to_int(_val(r, "required_amount"))
            fee_paid[str(activity_id)] += _to_int(_val(r, "paid_amount"))

    receipt_expense: dict[str, int] = defaultdict(int)
    evidence_by_activity: dict[str, list[str]] = defaultdict(list)
    for receipt in receipts:
        activity_id = _val(receipt, "activity_report_id")
        if not activity_id:
            continue
        receipt_expense[str(activity_id)] += _to_int(_val(receipt, "amount"))
        evidence_by_activity[str(activity_id)].append(str(_val(receipt, "evidence_status", "pending")))

    transaction_expense: dict[str, int] = defaultdict(int)
    for tx in transactions:
        activity_id = _val(tx, "linked_activity_id")
        if activity_id:
            transaction_expense[str(activity_id)] += _to_int(_val(tx, "withdraw_amount"))

    rows: list[dict[str, Any]] = []
    for activity in activities:
        if not _in_range(_val(activity, "activity_date"), start_date, end_date):
            continue
        activity_id = str(_val(activity, "id"))
        statuses = evidence_by_activity.get(activity_id, [])
        if not statuses and (receipt_expense[activity_id] or transaction_expense[activity_id]):
            evidence_status = "missing"
        elif any(s in {"missing", "need_check", "pending"} for s in statuses):
            evidence_status = "need_check"
        else:
            evidence_status = "ok"
        expense = receipt_expense[activity_id] + transaction_expense[activity_id]
        rows.append({
            "activity_id": activity_id,
            "activity_title": _val(activity, "title"),
            "activity_date": _date_value(_val(activity, "activity_date")).isoformat() if _date_value(_val(activity, "activity_date")) else None,
            "participant_count": participant_count[activity_id],
            "expected_income": fee_required[activity_id],
            "actual_income": fee_paid[activity_id],
            "expense_amount": expense,
            "balance_amount": fee_paid[activity_id] - expense,
            "evidence_status": evidence_status,
            "report_status": _val(activity, "status"),
            "target_url": f"/activities/{activity_id}",
            "activity_fee_url": f"/activities/{activity_id}?tab=activity-fee",
            "evidence_url": f"/activities/{activity_id}?tab=evidence",
            "files_url": f"/activities/{activity_id}?tab=files",
            "audit_package_url": f"/activities/{activity_id}?tab=audit",
        })
    return rows


def ensure_default_categories(db: Session) -> None:
    from app.models import BudgetCategory

    existing = {
        (c.name, c.type)
        for c in db.scalars(select(BudgetCategory))
    }
    changed = False
    for name, category_type, sort_order in DEFAULT_BUDGET_CATEGORIES:
        if (name, category_type) in existing:
            continue
        db.add(BudgetCategory(name=name, type=category_type, sort_order=sort_order, is_active=True))
        changed = True
    if changed:
        db.commit()


def _transaction_stmt(start_date: date | None = None, end_date: date | None = None):
    from app.models import BankTransaction

    stmt = select(BankTransaction)
    if start_date:
        stmt = stmt.where(BankTransaction.transaction_datetime >= datetime.combine(start_date, datetime.min.time()))
    if end_date:
        stmt = stmt.where(BankTransaction.transaction_datetime <= datetime.combine(end_date, datetime.max.time()))
    return stmt


def _receipt_stmt(start_date: date | None = None, end_date: date | None = None):
    from app.models import Receipt

    stmt = select(Receipt)
    if start_date:
        stmt = stmt.where(Receipt.receipt_date >= start_date)
    if end_date:
        stmt = stmt.where(Receipt.receipt_date <= end_date)
    return stmt


def get_budget_summary(
    db: Session,
    *,
    period: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    operating_quarter: str | None = None,
) -> dict[str, Any]:
    from app.models import PaymentRecord
    from app.services.membership_fee_policy import preview_membership_fee_generation

    # Apply operating_quarter date override for transactions
    eff_start = start_date
    eff_end = end_date
    if operating_quarter:
        eff_start, eff_end = quarter_date_range_from_str(operating_quarter)

    transactions = list(db.scalars(_transaction_stmt(eff_start, eff_end)))
    if period:
        membership_preview = preview_membership_fee_generation(db=db, period=period)
        membership_records = [
            SimpleNamespace(
                id=row.existing_record_id,
                member_id=row.member_id,
                period=membership_preview.current_term,
                payment_type="membership_fee",
                required_amount=row.required_amount,
                paid_amount=row.paid_amount,
                status=row.status,
                refund_status=None,
                refund_amount=0,
            )
            for row in membership_preview.rows
        ]
        activity_records = list(
            db.scalars(
                select(PaymentRecord).where(
                    PaymentRecord.period == period,
                    PaymentRecord.payment_type != "membership_fee",
                )
            )
        )
        payment_records = [*membership_records, *activity_records]
    else:
        payment_records = list(db.scalars(select(PaymentRecord)))
    receipts = list(db.scalars(_receipt_stmt(eff_start, eff_end)))
    return compute_finance_summary(
        transactions,
        payment_records,
        receipts,
        period=period,
        start_date=eff_start,
        end_date=eff_end,
        operating_quarter=operating_quarter,
    )


def get_budget_cashflow(
    db: Session,
    *,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict[str, Any]]:
    return compute_cashflow(
        list(db.scalars(_transaction_stmt(start_date, end_date))),
        start_date=start_date,
        end_date=end_date,
    )


def get_budget_vs_actual(
    db: Session,
    *,
    period: str,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict[str, Any]]:
    from app.models import BudgetCategory, BudgetPlan

    ensure_default_categories(db)
    categories = list(db.scalars(select(BudgetCategory)))
    plans = list(db.scalars(select(BudgetPlan).where(BudgetPlan.period == period)))
    transactions = list(db.scalars(_transaction_stmt(start_date, end_date)))
    return compute_budget_vs_actual(
        categories,
        plans,
        transactions,
        period=period,
        start_date=start_date,
        end_date=end_date,
    )


def get_activity_settlements(
    db: Session,
    *,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict[str, Any]]:
    from app.models import ActivityParticipant, ActivityReport, BankTransaction, PaymentRecord, Receipt

    activities = list(db.scalars(select(ActivityReport).where(ActivityReport.deleted_at.is_(None))))
    participants = list(db.scalars(select(ActivityParticipant).where(
        or_(
            ActivityParticipant.status.is_(None),
            ActivityParticipant.status.notin_(INACTIVE_PARTICIPANT_STATUSES),
        )
    )))
    payment_records = list(db.scalars(select(PaymentRecord).where(
        and_(
            PaymentRecord.payment_type == "activity_fee",
            PaymentRecord.status.notin_(INACTIVE_ACTIVITY_FEE_STATUSES),
        )
    )))
    receipts = list(db.scalars(select(Receipt)))
    transactions = list(db.scalars(select(BankTransaction).where(BankTransaction.linked_activity_id.is_not(None))))
    return compute_activity_settlements(
        activities,
        participants,
        payment_records,
        receipts,
        transactions,
        start_date=start_date,
        end_date=end_date,
    )


def upsert_budget_plan(db: Session, *, period: str, category_id: UUID, planned_amount: int, note: str | None):
    from app.models import BudgetPlan

    existing = db.scalar(
        select(BudgetPlan).where(
            and_(BudgetPlan.period == period, BudgetPlan.category_id == category_id)
        )
    )
    if existing:
        existing.planned_amount = planned_amount
        existing.note = note
        db.commit()
        db.refresh(existing)
        return existing
    plan = BudgetPlan(period=period, category_id=category_id, planned_amount=planned_amount, note=note)
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan
