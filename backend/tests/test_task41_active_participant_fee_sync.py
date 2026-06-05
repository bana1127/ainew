from __future__ import annotations

from datetime import date
from types import SimpleNamespace

from app.services.budget_service import compute_activity_settlements, compute_finance_summary


def test_activity_settlement_excludes_removed_participants_and_cancelled_fees() -> None:
    activity_id = "activity-1"

    rows = compute_activity_settlements(
        activities=[
            SimpleNamespace(
                id=activity_id,
                title="조향 활동",
                activity_date=date(2026, 6, 3),
                status="completed",
            )
        ],
        participants=[
            SimpleNamespace(activity_report_id=activity_id, status="active"),
            SimpleNamespace(activity_report_id=activity_id, status="removed"),
            SimpleNamespace(activity_report_id=activity_id, status="cancelled"),
        ],
        payment_records=[
            SimpleNamespace(
                activity_report_id=activity_id,
                payment_type="activity_fee",
                required_amount=10000,
                paid_amount=10000,
                status="paid",
            ),
            SimpleNamespace(
                activity_report_id=activity_id,
                payment_type="activity_fee",
                required_amount=10000,
                paid_amount=0,
                status="cancelled",
            ),
            SimpleNamespace(
                activity_report_id=activity_id,
                payment_type="activity_fee",
                required_amount=10000,
                paid_amount=0,
                status="excluded",
            ),
        ],
        receipts=[],
        transactions=[],
    )

    assert rows[0]["participant_count"] == 1
    assert rows[0]["expected_income"] == 10000
    assert rows[0]["actual_income"] == 10000


def test_cancelled_activity_fee_is_not_receivable() -> None:
    summary = compute_finance_summary(
        transactions=[],
        payment_records=[
            SimpleNamespace(
                period="act-12345678",
                payment_type="activity_fee",
                required_amount=10000,
                paid_amount=0,
                status="cancelled",
            ),
            SimpleNamespace(
                period="act-12345678",
                payment_type="activity_fee",
                required_amount=10000,
                paid_amount=0,
                status="unpaid",
            ),
        ],
        receipts=[],
    )

    assert summary["receivable_amount"] == 10000
