from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from app.services.budget_service import compute_activity_settlements


def test_activity_settlement_sums_activity_fee_income_and_receipt_expense() -> None:
    activity_id = uuid4()
    rows = compute_activity_settlements(
        activities=[SimpleNamespace(id=activity_id, title="향수 만들기", activity_date="2026-04-01", status="draft")],
        participants=[
            SimpleNamespace(activity_report_id=activity_id),
            SimpleNamespace(activity_report_id=activity_id),
        ],
        payment_records=[
            SimpleNamespace(activity_report_id=activity_id, payment_type="activity_fee", required_amount=20000, paid_amount=20000),
            SimpleNamespace(activity_report_id=activity_id, payment_type="activity_fee", required_amount=20000, paid_amount=10000),
        ],
        receipts=[
            SimpleNamespace(activity_report_id=activity_id, amount=15000, evidence_status="approved"),
        ],
        transactions=[],
    )

    assert rows[0]["participant_count"] == 2
    assert rows[0]["expected_income"] == 40000
    assert rows[0]["actual_income"] == 30000
    assert rows[0]["expense_amount"] == 15000
    assert rows[0]["balance_amount"] == 15000
