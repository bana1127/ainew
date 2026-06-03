from __future__ import annotations

from types import SimpleNamespace

from app.services.budget_service import compute_finance_summary


def test_period_income_expense_net_change() -> None:
    summary = compute_finance_summary(
        transactions=[
            SimpleNamespace(deposit_amount=100000, withdraw_amount=0, balance=100000, transaction_datetime="2026-03-01T09:00:00"),
            SimpleNamespace(deposit_amount=0, withdraw_amount=35000, balance=65000, transaction_datetime="2026-03-02T09:00:00"),
        ],
        payment_records=[],
        receipts=[],
        start_date=None,
        end_date=None,
    )

    assert summary["total_income"] == 100000
    assert summary["total_expense"] == 35000
    assert summary["net_change"] == 65000
    assert summary["current_balance"] == 65000


def test_membership_and_activity_unpaid_are_receivable() -> None:
    summary = compute_finance_summary(
        transactions=[],
        payment_records=[
            SimpleNamespace(period="2026-1", payment_type="membership_fee", required_amount=10000, paid_amount=0, status="unpaid"),
            SimpleNamespace(period="2026-1", payment_type="activity_fee", required_amount=25000, paid_amount=10000, status="partial"),
        ],
        receipts=[],
        period="2026-1",
    )

    assert summary["receivable_amount"] == 25000
