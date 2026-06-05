"""Tests for budget exclusion logic (Task 43)."""
from __future__ import annotations

from types import SimpleNamespace

from app.services.budget_service import (
    _is_budget_excluded,
    _is_income_excluded,
    _is_expense_excluded,
    compute_finance_summary,
)


def _tx(deposit=0, withdraw=0, dt="2026-04-01T09:00:00",
        payment_type=None, exclude_budget=False,
        exclude_income=False, exclude_expense=False):
    return SimpleNamespace(
        deposit_amount=deposit,
        withdraw_amount=withdraw,
        balance=None,
        transaction_datetime=dt,
        payment_type=payment_type,
        linked_activity_id=None,
        review_status="open",
        match_status="unmatched",
        exclude_from_budget=exclude_budget,
        exclude_from_income=exclude_income,
        exclude_from_expense=exclude_expense,
    )


def test_is_budget_excluded_false_by_default() -> None:
    tx = _tx(deposit=10000)
    assert _is_budget_excluded(tx) is False


def test_is_budget_excluded_true_when_flag_set() -> None:
    tx = _tx(deposit=10000, exclude_budget=True)
    assert _is_budget_excluded(tx) is True


def test_is_income_excluded_by_budget_flag() -> None:
    tx = _tx(deposit=10000, exclude_budget=True)
    assert _is_income_excluded(tx) is True


def test_is_income_excluded_by_income_flag() -> None:
    tx = _tx(deposit=10000, exclude_income=True)
    assert _is_income_excluded(tx) is True


def test_is_expense_excluded_by_expense_flag() -> None:
    tx = _tx(withdraw=5000, exclude_expense=True)
    assert _is_expense_excluded(tx) is True


def test_exclude_income_transaction_removed_from_total() -> None:
    txs = [
        _tx(deposit=100000),
        _tx(deposit=20000, exclude_income=True),  # 제외
    ]
    summary = compute_finance_summary(transactions=txs, payment_records=[], receipts=[])
    assert summary["total_income"] == 100000
    assert summary["excluded_income_amount"] == 20000


def test_exclude_expense_transaction_removed_from_total() -> None:
    txs = [
        _tx(withdraw=50000),
        _tx(withdraw=10000, exclude_expense=True),  # 제외
    ]
    summary = compute_finance_summary(transactions=txs, payment_records=[], receipts=[])
    assert summary["total_expense"] == 50000
    assert summary["excluded_expense_amount"] == 10000


def test_excluded_transaction_remains_in_original_list() -> None:
    """제외된 거래는 원본 transactions 리스트에서 사라지면 안 된다."""
    txs = [
        _tx(deposit=100000),
        _tx(deposit=50000, exclude_budget=True),
    ]
    # compute_finance_summary는 내부적으로 필터링하지만
    # 원본 리스트는 변경하지 않는다
    original_count = len(txs)
    compute_finance_summary(transactions=txs, payment_records=[], receipts=[])
    assert len(txs) == original_count  # 원본 보존


def test_both_income_and_expense_excluded() -> None:
    txs = [
        _tx(deposit=80000),
        _tx(deposit=20000, exclude_budget=True),  # 수입도 지출도 제외
        _tx(withdraw=30000),
        _tx(withdraw=10000, exclude_budget=True),  # 수입도 지출도 제외
    ]
    summary = compute_finance_summary(transactions=txs, payment_records=[], receipts=[])
    assert summary["total_income"] == 80000
    assert summary["total_expense"] == 30000
