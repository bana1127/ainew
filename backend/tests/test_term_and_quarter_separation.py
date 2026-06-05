"""Tests ensuring term (학기) and operating quarter are properly separated (Task 43)."""
from __future__ import annotations

from datetime import date

from app.services.term_service import get_term_for_date, parse_term
from app.services.quarter_service import get_operating_quarter


# ─── Term service ─────────────────────────────────────────────────────────────

def test_membership_fee_period_is_semester_not_quarter() -> None:
    """회비 period는 '2026-1' 같은 학기 값이어야 하며 분기 형식이 아니어야 함."""
    term = get_term_for_date(date(2026, 3, 1))
    assert term == "2026-1"
    assert "Q" not in term  # 분기 형식이 아님


def test_march_payment_uses_semester_period() -> None:
    """2026년 3월 회비 납부는 학기 2026-1, 예산 분기 2026-Q2에 포함."""
    term = get_term_for_date(date(2026, 3, 15))
    quarter = get_operating_quarter(date(2026, 3, 15))
    assert term == "2026-1"
    assert quarter == "2026-Q2"
    # 회비 기준과 예산 기준이 서로 독립적
    assert term != quarter


def test_membership_fee_unpaid_uses_semester_period() -> None:
    """회비 미납자 조회는 학기 기준 2026-1로 해야 하며 분기 Q2가 아님."""
    term = get_term_for_date(date(2026, 4, 1))
    assert term == "2026-1"  # 4월 → 1학기
    assert term != "2026-Q2"


def test_semester_1_range() -> None:
    """1학기는 3월~8월."""
    for month in [3, 4, 5, 6, 7, 8]:
        t = get_term_for_date(date(2026, month, 1))
        assert t == "2026-1", f"month={month} should be 2026-1"


def test_semester_2_range() -> None:
    """2학기는 9월~2월(다음 해). YYYY는 학년도 기준."""
    for month in [9, 10, 11, 12]:
        t = get_term_for_date(date(2026, month, 1))
        assert t == "2026-2", f"month={month} should be 2026-2"
    for month in [1, 2]:
        t = get_term_for_date(date(2027, month, 1))
        assert t == "2026-2", f"2027-{month} should be 2026-2"


def test_parse_term_valid() -> None:
    assert parse_term("2026-1") == (2026, 1)
    assert parse_term("2026-2") == (2026, 2)


def test_quarter_filter_independent_from_membership_period() -> None:
    """예산 분기 필터는 membership_fee period와 독립적으로 동작한다."""
    # 2026-Q2 기간 (3~5월)에 납부된 회비라도 period는 여전히 2026-1
    payment_date = date(2026, 5, 10)
    period = get_term_for_date(payment_date)
    quarter = get_operating_quarter(payment_date)
    assert period == "2026-1"    # 회비는 학기 기준
    assert quarter == "2026-Q2"  # 예산은 분기 기준


def test_budget_q2_includes_membership_fee_by_transaction_date() -> None:
    """예산 Q2 집계 시 3/4/5월 회비 입금은 Q2 수입으로 집계 (거래일 기준)."""
    from types import SimpleNamespace
    from app.services.budget_service import compute_finance_summary

    txs = [
        SimpleNamespace(
            deposit_amount=10000, withdraw_amount=0, balance=None,
            transaction_datetime="2026-05-10T09:00:00",
            payment_type="membership_fee",
            linked_activity_id=None, review_status="open",
            match_status="matched",
            exclude_from_budget=False, exclude_from_income=False,
            exclude_from_expense=False,
        )
    ]
    summary = compute_finance_summary(
        transactions=txs,
        payment_records=[],
        receipts=[],
        operating_quarter="2026-Q2",
    )
    # 회비 납부 거래가 Q2 수입에 포함
    assert summary["total_income"] == 10000
    assert summary["membership_fee_income"] == 10000
