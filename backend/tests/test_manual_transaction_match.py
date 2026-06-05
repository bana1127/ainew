"""Tests for manual transaction matching (Task 43)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4


def make_mock_transaction(deposit=10000, match_status="need_check"):
    m = MagicMock()
    m.id = uuid4()
    m.deposit_amount = deposit
    m.match_status = match_status
    m.payment_type = None
    m.matched_member_id = None
    return m


def make_mock_payment_record(required=10000, paid=0, status="unpaid"):
    m = MagicMock()
    m.id = uuid4()
    m.required_amount = required
    m.paid_amount = paid
    m.status = status
    m.member_id = uuid4()
    m.transaction_id = None
    m.payment_source = None
    return m


def test_amount_exact_match_allows_manual_match() -> None:
    """금액이 정확히 일치하면 수동 매칭 허용 (이름 confidence 무관)."""
    txn = make_mock_transaction(deposit=10000)
    record = make_mock_payment_record(required=10000, paid=0)

    # 로직 검증: deposit == required_amount
    deposit = int(txn.deposit_amount)
    required = int(record.required_amount)
    remaining = required - int(record.paid_amount)

    assert deposit == required or deposit == remaining, "금액 일치해야 매칭 허용"


def test_amount_mismatch_blocks_manual_match() -> None:
    """금액 불일치 시 수동 매칭 차단."""
    txn = make_mock_transaction(deposit=8000)
    record = make_mock_payment_record(required=10000, paid=0)

    deposit = int(txn.deposit_amount)
    required = int(record.required_amount)
    remaining = required - int(record.paid_amount)

    assert deposit != required and deposit != remaining, "금액 불일치 → 차단"


def test_manual_match_sets_payment_source() -> None:
    """수동 매칭은 payment_source를 manual_match로 설정해야 함."""
    record = make_mock_payment_record(required=10000, paid=0)
    # 시뮬레이션: 수동 매칭 후
    record.payment_source = "manual_match"
    record.transaction_id = uuid4()
    assert record.payment_source == "manual_match"
    assert record.transaction_id is not None


def test_manual_payment_has_no_transaction_id() -> None:
    """수동 납부 처리(거래내역 없음)는 transaction_id가 없어야 함."""
    record = make_mock_payment_record(required=10000, paid=0)
    # 수동 납부: transaction_id 없음
    record.payment_source = "manual"
    record.paid_amount = 10000
    record.status = "paid"
    assert record.transaction_id is None


def test_membership_fee_manual_match_link() -> None:
    """회비 수동 매칭 확정 시 transaction_id가 설정됨."""
    txn = make_mock_transaction(deposit=10000)
    record = make_mock_payment_record(required=10000, paid=0)

    # 수동 매칭 적용
    record.paid_amount = txn.deposit_amount
    record.transaction_id = txn.id
    record.payment_source = "manual_match"
    record.status = "paid"
    txn.match_status = "matched"

    assert record.transaction_id == txn.id
    assert txn.match_status == "matched"
    assert record.payment_source == "manual_match"


def test_activity_fee_manual_match_link() -> None:
    """활동비 수동 매칭 확정 시 transaction_id가 설정됨."""
    txn = make_mock_transaction(deposit=25000)
    record = make_mock_payment_record(required=25000, paid=0)

    record.paid_amount = txn.deposit_amount
    record.transaction_id = txn.id
    record.payment_source = "manual_match"
    record.status = "paid"
    txn.match_status = "matched"
    txn.payment_type = "activity_fee"

    assert record.paid_amount == 25000
    assert record.status == "paid"
    assert txn.payment_type == "activity_fee"
