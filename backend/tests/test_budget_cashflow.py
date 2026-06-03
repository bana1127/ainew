from __future__ import annotations

from types import SimpleNamespace

from app.services.budget_service import compute_cashflow


def test_cashflow_groups_income_and_expense_by_month() -> None:
    rows = compute_cashflow([
        SimpleNamespace(transaction_datetime="2026-01-05T10:00:00", deposit_amount=30000, withdraw_amount=0),
        SimpleNamespace(transaction_datetime="2026-01-08T10:00:00", deposit_amount=0, withdraw_amount=12000),
        SimpleNamespace(transaction_datetime="2026-02-01T10:00:00", deposit_amount=5000, withdraw_amount=0),
    ])

    assert rows == [
        {"bucket": "2026-01", "income": 30000, "expense": 12000, "net": 18000},
        {"bucket": "2026-02", "income": 5000, "expense": 0, "net": 5000},
    ]
