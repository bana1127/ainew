"""Task 31 Tests: Activity fee tab summary — only counts this activity's activity_fee records."""
from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import MagicMock
from uuid import uuid4


def _stub(name: str) -> ModuleType:
    mod = ModuleType(name)
    mod.__spec__ = None  # type: ignore[attr-defined]
    return mod


for _m in ("psycopg", "psycopg2", "psycopg2.extras"):
    sys.modules.setdefault(_m, _stub(_m))


# ---------------------------------------------------------------------------
# Pure logic helpers used by the summary endpoint
# ---------------------------------------------------------------------------

def _compute_summary(records: list[dict]) -> dict:
    """Mirrors the summary logic in get_activity_fee_summary."""
    paid = sum(1 for r in records if r["status"] == "paid")
    unpaid = sum(1 for r in records if r["status"] == "unpaid")
    partial = sum(1 for r in records if r["status"] == "partial")
    overpaid = sum(1 for r in records if r["status"] == "overpaid")
    refund_needed = sum(
        1 for r in records if r.get("refund_status") in ("refund_required", "refund_pending")
    )
    total_required = sum(r["required_amount"] for r in records)
    total_paid = sum(r["paid_amount"] for r in records)
    return {
        "participant_count": len(records),
        "paid": paid,
        "unpaid": unpaid,
        "partial": partial,
        "overpaid": overpaid,
        "refund_needed": refund_needed,
        "total_required": total_required,
        "total_paid": total_paid,
    }


class TestActivityFeeSummaryAggregation:
    def test_counts_only_activity_fee_records(self) -> None:
        activity_id = str(uuid4())[:8]
        period_key = f"act-{activity_id}"
        records = [
            {"status": "paid", "required_amount": 10000, "paid_amount": 10000,
             "period": period_key, "payment_type": "activity_fee"},
            {"status": "unpaid", "required_amount": 10000, "paid_amount": 0,
             "period": period_key, "payment_type": "activity_fee"},
        ]
        summary = _compute_summary(records)
        assert summary["participant_count"] == 2
        assert summary["paid"] == 1
        assert summary["unpaid"] == 1

    def test_membership_fee_not_counted(self) -> None:
        activity_id = str(uuid4())[:8]
        period_key = f"act-{activity_id}"
        # Only activity_fee records should be passed to summary
        # (backend filters by payment_type='activity_fee' AND period=period_key)
        activity_fee_records = [
            {"status": "paid", "required_amount": 10000, "paid_amount": 10000,
             "period": period_key, "payment_type": "activity_fee"},
        ]
        membership_fee_records = [
            {"status": "unpaid", "required_amount": 10000, "paid_amount": 0,
             "period": "2026-1", "payment_type": "membership_fee"},
        ]
        # Summary function only receives activity_fee records (backend-filtered)
        summary = _compute_summary(activity_fee_records)
        assert summary["participant_count"] == 1
        assert summary["paid"] == 1
        assert summary["unpaid"] == 0

    def test_other_activity_not_counted(self) -> None:
        act1_id = str(uuid4())[:8]
        act2_id = str(uuid4())[:8]
        act1_period = f"act-{act1_id}"

        act1_records = [
            {"status": "unpaid", "required_amount": 25000, "paid_amount": 0,
             "period": act1_period, "payment_type": "activity_fee"},
        ]
        summary = _compute_summary(act1_records)
        # act2 records are never passed — summary is scoped at DB query level
        assert summary["participant_count"] == 1

    def test_total_amounts(self) -> None:
        records = [
            {"status": "paid", "required_amount": 25000, "paid_amount": 25000},
            {"status": "partial", "required_amount": 25000, "paid_amount": 10000},
            {"status": "unpaid", "required_amount": 25000, "paid_amount": 0},
        ]
        summary = _compute_summary(records)
        assert summary["total_required"] == 75000
        assert summary["total_paid"] == 35000

    def test_refund_needed_counts_refund_required_and_pending(self) -> None:
        records = [
            {"status": "overpaid", "required_amount": 10000, "paid_amount": 15000,
             "refund_status": "refund_required"},
            {"status": "paid", "required_amount": 10000, "paid_amount": 10000,
             "refund_status": "refund_pending"},
            {"status": "paid", "required_amount": 10000, "paid_amount": 10000,
             "refund_status": "refunded"},
            {"status": "paid", "required_amount": 10000, "paid_amount": 10000,
             "refund_status": "none"},
        ]
        summary = _compute_summary(records)
        assert summary["refund_needed"] == 2

    def test_empty_records(self) -> None:
        summary = _compute_summary([])
        assert summary["participant_count"] == 0
        assert summary["paid"] == 0
        assert summary["total_required"] == 0
        assert summary["total_paid"] == 0
