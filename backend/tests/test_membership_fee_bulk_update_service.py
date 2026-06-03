from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace
from uuid import uuid4

import pytest

from app.services import membership_fee_bulk_update_service as svc


class _Column:
    def in_(self, values):
        return ("in", values)

    def __eq__(self, other):  # pragma: no cover - only used to build fake clauses
        return ("eq", other)


class _Select:
    def __init__(self, model):
        self.model = model

    def where(self, *_args, **_kwargs):
        return self


class _FakeMember:
    id = _Column()

    def __init__(self, name: str = "Member", student_id: str | None = None):
        self.id = uuid4()
        self.name = name
        self.student_id = student_id


class _FakePaymentRecord:
    id = _Column()
    period = _Column()
    payment_type = _Column()

    def __init__(
        self,
        member: _FakeMember,
        *,
        period: str = "2026-1",
        payment_type: str = "membership_fee",
        required_amount: int = 10000,
        paid_amount: int = 0,
        status: str = "unpaid",
    ):
        self.id = uuid4()
        self.member_id = member.id
        self.period = period
        self.payment_type = payment_type
        self.required_amount = required_amount
        self.paid_amount = paid_amount
        self.status = status


class _FakeAssistantActionProposal:
    pass


class _FakeSession:
    def __init__(self, records=None, members=None, proposals=None):
        self.records = list(records or [])
        self.members = list(members or [])
        self.proposals = dict(proposals or {})
        self.committed = False

    def scalars(self, query):
        if query.model is _FakePaymentRecord:
            return self.records
        if query.model is _FakeMember:
            return self.members
        return []

    def get(self, model, obj_id):
        if model is _FakeAssistantActionProposal:
            return self.proposals.get(obj_id)
        if model is _FakePaymentRecord:
            return next((record for record in self.records if record.id == obj_id), None)
        return None

    def commit(self):
        self.committed = True


@pytest.fixture(autouse=True)
def fake_service_dependencies(monkeypatch):
    models = ModuleType("app.models")
    models.Member = _FakeMember
    models.PaymentRecord = _FakePaymentRecord
    monkeypatch.setitem(sys.modules, "app.models", models)

    assistant_action = ModuleType("app.models.assistant_action")
    assistant_action.AssistantActionProposal = _FakeAssistantActionProposal
    monkeypatch.setitem(sys.modules, "app.models.assistant_action", assistant_action)

    action_service = ModuleType("app.services.assistant_action_service")
    action_service.create_action_proposal = lambda *args, **kwargs: SimpleNamespace(id=uuid4())
    monkeypatch.setitem(sys.modules, "app.services.assistant_action_service", action_service)

    monkeypatch.setattr(svc, "select", lambda model: _Select(model))


def test_preview_does_not_mutate_membership_fee_records() -> None:
    member = _FakeMember()
    record = _FakePaymentRecord(member, required_amount=15000)
    db = _FakeSession(records=[record], members=[member])

    result = svc.preview_bulk_update(
        db=db,
        period="2026-1",
        payment_record_ids=[str(record.id)],
        operation="mark_paid",
    )

    assert result.summary.will_change == 1
    assert record.paid_amount == 0
    assert record.status == "unpaid"


def test_preview_rejects_activity_fee_records_and_keeps_them_unchanged() -> None:
    member = _FakeMember()
    membership = _FakePaymentRecord(member, payment_type="membership_fee", required_amount=10000)
    activity = _FakePaymentRecord(member, payment_type="activity_fee", required_amount=5000)
    db = _FakeSession(records=[membership, activity], members=[member])

    with pytest.raises(ValueError, match="Only membership_fee records can be bulk-updated"):
        svc.preview_bulk_update(
            db=db,
            period="2026-1",
            payment_record_ids=[str(membership.id), str(activity.id)],
            operation="mark_paid",
        )

    assert activity.paid_amount == 0
    assert activity.status == "unpaid"
    assert membership.paid_amount == 0
    assert membership.status == "unpaid"


def test_preview_rejects_missing_payment_record_ids() -> None:
    db = _FakeSession()

    with pytest.raises(ValueError, match="PaymentRecord not found"):
        svc.preview_bulk_update(
            db=db,
            period="2026-1",
            payment_record_ids=[str(uuid4())],
            operation="mark_paid",
        )


def test_confirm_revalidates_scope_for_tampered_action_payload() -> None:
    member = _FakeMember()
    membership = _FakePaymentRecord(member, payment_type="membership_fee", required_amount=10000)
    activity = _FakePaymentRecord(member, payment_type="activity_fee", required_amount=5000)
    proposal = SimpleNamespace(
        id=uuid4(),
        status="pending",
        payload_json={
            "period": "2026-1",
            "operation": "mark_paid",
            "payment_record_ids": [str(membership.id), str(activity.id)],
            "paid_amount_value": None,
        },
        preview_json={},
        confirmed_at=None,
        applied_at=None,
    )
    db = _FakeSession(
        records=[membership, activity],
        members=[member],
        proposals={proposal.id: proposal},
    )

    with pytest.raises(ValueError, match="Only membership_fee records can be bulk-updated"):
        svc.confirm_bulk_update(db, proposal.id)

    assert membership.paid_amount == 0
    assert membership.status == "unpaid"
    assert activity.paid_amount == 0
    assert activity.status == "unpaid"
    assert proposal.status == "pending"


def test_mark_unpaid_keeps_zero_required_records_exempt() -> None:
    member = _FakeMember()
    record = _FakePaymentRecord(
        member,
        required_amount=0,
        paid_amount=0,
        status="exempt",
    )
    db = _FakeSession(records=[record], members=[member])

    result = svc.preview_bulk_update(
        db=db,
        period="2026-1",
        payment_record_ids=[str(record.id)],
        operation="mark_unpaid",
    )

    assert result.rows[0].after_status == "exempt"
