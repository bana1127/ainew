"""Tests for quarter-based budget summary (Task 43)."""
from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

from app.services.budget_service import compute_finance_summary


def _tx(deposit=0, withdraw=0, balance=None, dt="2026-04-15T09:00:00",
        payment_type=None, exclude_budget=False, exclude_income=False, exclude_expense=False):
    return SimpleNamespace(
        deposit_amount=deposit,
        withdraw_amount=withdraw,
        balance=balance,
        transaction_datetime=dt,
        payment_type=payment_type,
        linked_activity_id=None,
        review_status="open",
        match_status="unmatched",
        exclude_from_budget=exclude_budget,
        exclude_from_income=exclude_income,
        exclude_from_expense=exclude_expense,
    )


def test_q2_operating_quarter_includes_only_q2_months() -> None:
    """2026-Q2 필터: 3/4/5월 거래만 포함."""
    txs = [
        _tx(deposit=10000, dt="2026-03-01T09:00:00"),  # Q2 포함
        _tx(deposit=20000, dt="2026-04-15T09:00:00"),  # Q2 포함
        _tx(deposit=5000, dt="2026-06-01T09:00:00"),   # Q3 제외
        _tx(deposit=3000, dt="2026-02-28T09:00:00"),   # Q1 제외
    ]
    summary = compute_finance_summary(
        transactions=txs,
        payment_records=[],
        receipts=[],
        operating_quarter="2026-Q2",
    )
    assert summary["total_income"] == 30000  # 10000 + 20000
    assert summary["operating_quarter"] == "2026-Q2"


def test_q1_includes_december_from_previous_year() -> None:
    """2026-Q1: 2025-12월 거래가 포함되어야 함."""
    txs = [
        _tx(deposit=10000, dt="2025-12-15T09:00:00"),  # 포함
        _tx(deposit=20000, dt="2026-01-10T09:00:00"),  # 포함
        _tx(deposit=5000, dt="2026-03-01T09:00:00"),   # Q2 제외
    ]
    summary = compute_finance_summary(
        transactions=txs,
        payment_records=[],
        receipts=[],
        operating_quarter="2026-Q1",
    )
    assert summary["total_income"] == 30000  # 10000 + 20000


def test_excluded_income_not_counted_in_total_income() -> None:
    """수입 제외 거래는 total_income에서 빠져야 함."""
    txs = [
        _tx(deposit=50000, dt="2026-04-01T09:00:00"),
        _tx(deposit=30000, dt="2026-04-10T09:00:00", exclude_income=True),
    ]
    summary = compute_finance_summary(
        transactions=txs,
        payment_records=[],
        receipts=[],
    )
    assert summary["total_income"] == 50000
    assert summary["excluded_income_amount"] == 30000
    assert summary["excluded_income_count"] == 1


def test_excluded_expense_not_counted_in_total_expense() -> None:
    """지출 제외 거래는 total_expense에서 빠져야 함."""
    txs = [
        _tx(withdraw=20000, dt="2026-04-01T09:00:00"),
        _tx(withdraw=10000, dt="2026-04-05T09:00:00", exclude_expense=True),
    ]
    summary = compute_finance_summary(
        transactions=txs,
        payment_records=[],
        receipts=[],
    )
    assert summary["total_expense"] == 20000
    assert summary["excluded_expense_amount"] == 10000


def test_budget_excluded_transaction_excluded_from_both() -> None:
    """exclude_from_budget=True이면 수입과 지출 모두에서 제외."""
    txs = [
        _tx(deposit=100000, dt="2026-04-01T09:00:00"),
        _tx(deposit=50000, dt="2026-04-02T09:00:00", exclude_budget=True),
    ]
    summary = compute_finance_summary(
        transactions=txs,
        payment_records=[],
        receipts=[],
    )
    assert summary["total_income"] == 100000


def test_excluded_transaction_still_present_in_input() -> None:
    """제외된 거래는 원본 목록(transactions)에는 여전히 있어야 함."""
    txs = [
        _tx(deposit=100000, dt="2026-04-01T09:00:00"),
        _tx(deposit=50000, dt="2026-04-02T09:00:00", exclude_budget=True),
    ]
    # 원본 리스트 길이는 여전히 2
    assert len(txs) == 2


def test_membership_fee_income_breakdown() -> None:
    """회비 수입이 membership_fee_income에 올바르게 분류되어야 함."""
    txs = [
        _tx(deposit=10000, dt="2026-04-01T09:00:00", payment_type="membership_fee"),
        _tx(deposit=20000, dt="2026-04-02T09:00:00", payment_type="activity_fee"),
        _tx(deposit=5000, dt="2026-04-03T09:00:00", payment_type="other"),
    ]
    summary = compute_finance_summary(
        transactions=txs,
        payment_records=[],
        receipts=[],
    )
    assert summary["membership_fee_income"] == 10000
    assert summary["activity_fee_income"] == 20000
    assert summary["other_income"] == 5000
