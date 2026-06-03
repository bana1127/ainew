from types import SimpleNamespace
from uuid import uuid4

from app.services.membership_fee_policy import (
    decide_membership_fee,
    normalize_term,
    payment_status,
)


def member(**kwargs):
    defaults = {
        "id": uuid4(),
        "name": "김테스트",
        "student_id": "20260001",
        "department": "테스트학과",
        "joined_term": None,
        "term_code": None,
        "is_executive": False,
        "role": None,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_normalize_term_variants():
    assert normalize_term("26-1학기") == "2026-1"
    assert normalize_term("2026-1학기") == "2026-1"
    assert normalize_term("2026-1") == "2026-1"
    assert normalize_term("26년 1학기") == "2026-1"
    assert normalize_term("2026년 1학기") == "2026-1"


def test_joined_current_term_is_new_member_fee():
    row = decide_membership_fee(member(joined_term="2026-1"), current_term="2026-1")

    assert row.fee_tier == "new"
    assert row.required_amount == 15000
    assert row.status == "unpaid"


def test_previous_joined_term_is_existing_member_fee():
    row = decide_membership_fee(member(joined_term="2025-2"), current_term="2026-1")

    assert row.fee_tier == "existing"
    assert row.required_amount == 10000


def test_payment_status_rules():
    assert payment_status(0, 0) == "exempt"
    assert payment_status(0, 10000) == "unpaid"
    assert payment_status(5000, 10000) == "partial"
    assert payment_status(10000, 10000) == "paid"
    assert payment_status(12000, 10000) == "overpaid"
