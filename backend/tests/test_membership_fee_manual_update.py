from __future__ import annotations

import sys
from types import ModuleType
from uuid import uuid4

import pytest

from app.services.membership_fee_management_service import apply_membership_record_manual_update


class _PaymentRecord:
    def __init__(self, *, payment_type="membership_fee", required_amount=15000, paid_amount=0, status="unpaid"):
        self.id = uuid4()
        self.payment_type = payment_type
        self.required_amount = required_amount
        self.paid_amount = paid_amount
        self.status = status
        self.transaction_id = None
        self.payment_source = None
        self.manual_note = None


class _PaymentAdjustmentLog:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class _FakeDb:
    def __init__(self, record):
        self.record = record
        self.added = []
        self.committed = False

    def get(self, model, obj_id):
        if model is _PaymentRecord and obj_id == self.record.id:
            return self.record
        return None

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.committed = True

    def refresh(self, obj):
        return None


@pytest.fixture(autouse=True)
def fake_models(monkeypatch):
    models = ModuleType("app.models")
    models.PaymentRecord = _PaymentRecord
    monkeypatch.setitem(sys.modules, "app.models", models)

    payment_model = ModuleType("app.models.payment")
    payment_model.PaymentAdjustmentLog = _PaymentAdjustmentLog
    monkeypatch.setitem(sys.modules, "app.models.payment", payment_model)


def test_manual_paid_update_does_not_require_transaction_match():
    record = _PaymentRecord(required_amount=15000, paid_amount=0, status="unpaid")
    db = _FakeDb(record)

    updated = apply_membership_record_manual_update(
        db,
        payment_record_id=record.id,
        paid_amount=15000,
        manual_note="현금 수납",
    )

    assert updated.status == "paid"
    assert updated.transaction_id is None
    assert updated.payment_source == "manual"
    assert updated.manual_note == "현금 수납"
    assert db.committed is True
    assert len(db.added) == 1


def test_manual_update_rejects_activity_fee_record():
    record = _PaymentRecord(payment_type="activity_fee", required_amount=5000)
    db = _FakeDb(record)

    with pytest.raises(ValueError, match="Only membership_fee"):
        apply_membership_record_manual_update(
            db,
            payment_record_id=record.id,
            paid_amount=5000,
        )

    assert record.status == "unpaid"
    assert db.committed is False
