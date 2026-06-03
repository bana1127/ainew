from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from app.services.budget_service import compute_budget_vs_actual


def test_budget_plan_compares_planned_and_actual_amounts() -> None:
    membership = SimpleNamespace(id=uuid4(), name="회비", type="income", sort_order=10, is_active=True)
    rent = SimpleNamespace(id=uuid4(), name="대관비", type="expense", sort_order=20, is_active=True)
    rows = compute_budget_vs_actual(
        categories=[membership, rent],
        plans=[
            SimpleNamespace(period="2026-1", category_id=membership.id, planned_amount=50000, note="학기 회비"),
            SimpleNamespace(period="2026-1", category_id=rent.id, planned_amount=20000, note=None),
        ],
        transactions=[
            SimpleNamespace(payment_type="membership_fee", deposit_amount=30000, withdraw_amount=0, budget_category_id=None, memo="", transaction_datetime="2026-03-01T00:00:00"),
            SimpleNamespace(payment_type=None, deposit_amount=0, withdraw_amount=25000, budget_category_id=rent.id, memo="대관", transaction_datetime="2026-03-02T00:00:00"),
        ],
        period="2026-1",
    )

    by_name = {row["category_name"]: row for row in rows}
    assert by_name["회비"]["planned_amount"] == 50000
    assert by_name["회비"]["actual_amount"] == 30000
    assert by_name["대관비"]["actual_amount"] == 25000
    assert by_name["대관비"]["over_budget"] is True
