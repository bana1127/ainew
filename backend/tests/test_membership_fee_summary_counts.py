from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from app.services import membership_fee_management_service as svc


def _row(*, status: str, required: int, paid: int, existing=True):
    return SimpleNamespace(
        member_id=uuid4(),
        status=status,
        required_amount=required,
        paid_amount=paid,
        existing_record_id=uuid4() if existing else None,
    )


def test_membership_fee_summary_counts_missing_and_unpaid(monkeypatch):
    preview = SimpleNamespace(
        current_term="2026-1",
        new_member_fee=15000,
        rows=[
            _row(status="unpaid", required=15000, paid=0, existing=False),
            _row(status="partial", required=10000, paid=4000),
            _row(status="need_check", required=10000, paid=0),
            _row(status="paid", required=10000, paid=10000),
            _row(status="exempt", required=0, paid=0),
        ],
    )
    monkeypatch.setattr(svc, "preview_membership_fee_generation", lambda **kwargs: preview)

    summary = svc.get_membership_fee_summary(None, period="2026-1")

    assert summary.total_members == 5
    assert summary.unpaid_count == 1
    assert summary.partial_count == 1
    assert summary.need_check_count == 1
    assert summary.exempt_count == 1
    assert summary.missing_record_count == 1
    assert summary.receivable_amount == 31000
