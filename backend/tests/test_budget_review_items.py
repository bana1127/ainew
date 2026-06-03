from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace
from uuid import uuid4

from app.services.budget_review_service import build_review_items, preview_transaction_classification


def test_payment_review_item_target_urls_keep_domains_separate() -> None:
    activity_id = uuid4()
    items = build_review_items(
        payment_records=[
            SimpleNamespace(id=uuid4(), period="2026-1", payment_type="membership_fee", required_amount=10000, paid_amount=0, status="unpaid", activity_report_id=None, member_name="A"),
            SimpleNamespace(id=uuid4(), period="2026-1", payment_type="activity_fee", required_amount=20000, paid_amount=0, status="unpaid", activity_report_id=activity_id, member_name="B"),
        ],
        transactions=[],
        receipts=[],
        budget_rows=[],
        period="2026-1",
    )

    by_type = {item["type"]: item for item in items}
    assert by_type["membership_fee_unpaid"]["target_url"] == "/payments"
    assert by_type["activity_fee_unpaid"]["target_url"] == f"/activities/{activity_id}?tab=activity-fee"


def test_unclassified_transaction_and_missing_evidence_are_review_items() -> None:
    tx_id = uuid4()
    items = build_review_items(
        payment_records=[],
        transactions=[
            SimpleNamespace(id=tx_id, payment_type=None, match_status="unmatched", review_status="open", deposit_amount=0, withdraw_amount=12000, memo="문구점", linked_activity_id=None, transaction_datetime="2026-04-01T00:00:00"),
        ],
        receipts=[],
        budget_rows=[],
    )

    types = {item["type"] for item in items}
    assert "unclassified_transaction" in types
    assert "missing_evidence" in types


def test_transaction_classify_preview_does_not_mutate_db_before_confirm(monkeypatch) -> None:
    transaction_id = uuid4()
    transaction = SimpleNamespace(
        id=transaction_id,
        payment_type=None,
        budget_category_id=None,
        linked_activity_id=None,
        match_status="unmatched",
        review_status="open",
        review_note=None,
    )

    class FakeTransaction:
        pass

    class FakeDb:
        def get(self, model, obj_id):
            assert model is FakeTransaction
            assert obj_id == transaction_id
            return transaction

    action_service = ModuleType("app.services.assistant_action_service")
    action_service.create_action_proposal = lambda *args, **kwargs: SimpleNamespace(id=uuid4())
    monkeypatch.setitem(sys.modules, "app.services.assistant_action_service", action_service)

    models = ModuleType("app.models")
    models.BankTransaction = FakeTransaction
    monkeypatch.setitem(sys.modules, "app.models", models)

    result = preview_transaction_classification(
        FakeDb(),
        transaction_id=transaction_id,
        payload={"payment_type": "membership_fee", "review_status": "reviewed"},
    )

    assert result["requires_confirmation"] is True
    assert transaction.payment_type is None
    assert transaction.review_status == "open"
