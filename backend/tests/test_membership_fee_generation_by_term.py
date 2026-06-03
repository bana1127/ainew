from types import SimpleNamespace
from uuid import uuid4

from app.services.membership_fee_policy import build_membership_fee_plan


def member(**kwargs):
    defaults = {
        "id": uuid4(),
        "name": "김테스트",
        "student_id": "20260001",
        "department": "테스트학과",
        "joined_term": "2026-1",
        "term_code": None,
        "is_executive": False,
        "role": None,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def record(member_id, **kwargs):
    defaults = {
        "id": uuid4(),
        "member_id": member_id,
        "payment_type": "membership_fee",
        "paid_amount": 0,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_president_vice_president_and_officer_are_exempt():
    members = [
        member(name="회장", role="회장", is_executive=True),
        member(name="부회장", role="부회장", is_executive=True),
        member(name="임원", role="임원", is_executive=True),
    ]

    rows, summary = build_membership_fee_plan(members, [], current_term="2026-1")

    assert summary.executive_count == 3
    assert {row.officer_role for row in rows} == {"president", "vice_president", "officer"}
    assert all(row.required_amount == 0 for row in rows)
    assert all(row.status == "exempt" for row in rows)


def test_existing_record_is_updated_not_duplicated_and_paid_amount_preserved():
    m = member(joined_term="2025-2")
    existing = record(m.id, paid_amount=5000)

    rows, summary = build_membership_fee_plan([m], [existing], current_term="2026-1")

    assert summary.created_count == 0
    assert summary.updated_count == 1
    assert summary.preserved_paid_count == 1
    assert rows[0].action == "update"
    assert rows[0].existing_record_id == existing.id
    assert rows[0].paid_amount == 5000
    assert rows[0].required_amount == 10000
    assert rows[0].status == "partial"


def test_changed_to_executive_recalculates_required_zero_and_exempt():
    m = member(joined_term="2025-2", role="임원", is_executive=True)
    existing = record(m.id, paid_amount=5000)

    rows, _summary = build_membership_fee_plan([m], [existing], current_term="2026-1")

    assert rows[0].fee_tier == "executive"
    assert rows[0].required_amount == 0
    assert rows[0].paid_amount == 5000
    assert rows[0].status == "exempt"
