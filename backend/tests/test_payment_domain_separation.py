from __future__ import annotations

import sys
import importlib
from types import ModuleType
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest


def _stub_module(name: str) -> ModuleType:
    mod = ModuleType(name)
    mod.__spec__ = None  # type: ignore[attr-defined]
    return mod


for _mod_name in ("psycopg", "psycopg2", "psycopg2.extras"):
    sys.modules.setdefault(_mod_name, _stub_module(_mod_name))


class _AssistantExecuteResponseStub:
    def __init__(self, **kwargs):
        kwargs.setdefault("apply_payload", None)
        kwargs.setdefault("detail_url", None)
        kwargs.setdefault("activity_context", None)
        kwargs.setdefault("activity_candidates", None)
        kwargs.setdefault("activity_draft", None)
        self.__dict__.update(kwargs)


@pytest.fixture
def orchestrator_symbols(monkeypatch):
    previous_orchestrator = sys.modules.pop("app.agents.assistant_orchestrator", None)

    activity_resolver_stub = _stub_module("app.agents.activity_resolver")
    activity_resolver_stub.ActivityResolutionResult = SimpleNamespace  # type: ignore[attr-defined]
    activity_resolver_stub.resolve_activity_context = MagicMock()  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "app.agents.activity_resolver", activity_resolver_stub)

    assistant_schema_stub = _stub_module("app.schemas.assistant")
    assistant_schema_stub.AssistantExecuteResponse = _AssistantExecuteResponseStub  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "app.schemas.assistant", assistant_schema_stub)

    assistant_action_model_stub = _stub_module("app.models.assistant_action")
    assistant_action_model_stub.AssistantActionProposal = MagicMock  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "app.models.assistant_action", assistant_action_model_stub)

    module = importlib.import_module("app.agents.assistant_orchestrator")
    try:
        yield module.AssistantInput, module.AssistantOrchestrator
    finally:
        sys.modules.pop("app.agents.assistant_orchestrator", None)
        if previous_orchestrator is not None:
            sys.modules["app.agents.assistant_orchestrator"] = previous_orchestrator


def _activity_context(activity_id):
    return SimpleNamespace(
        mode="linked",
        activity_id=str(activity_id),
        activity_title="테스트 활동",
        confidence=1.0,
        candidates=[],
        draft=None,
    )


def test_membership_fee_manual_request_in_activity_does_not_call_activity_update(monkeypatch, orchestrator_symbols):
    AssistantInput, AssistantOrchestrator = orchestrator_symbols
    from app.agents.intent_router import IntentResult

    called = False

    def fake_apply_manual_payment_update(**kwargs):
        nonlocal called
        called = True
        raise AssertionError("membership_fee request must not touch activity_fee records")

    monkeypatch.setattr(
        "app.services.payment_manual_update_service.apply_manual_payment_update",
        fake_apply_manual_payment_update,
    )

    activity_id = uuid4()
    response = AssistantOrchestrator(MagicMock())._payment_manual_update(
        AssistantInput(message="박민서 회비 완납 처리", activity_id=activity_id),
        IntentResult("payment_manual_update", 0.9, "test"),
        _activity_context(activity_id),
    )

    assert called is False
    assert response.requires_confirmation is True
    assert response.apply_payload is None
    assert response.result["payment_type"] == "membership_fee"
    assert "회비" in response.message


def test_activity_fee_manual_request_does_not_use_membership_fee(monkeypatch, orchestrator_symbols):
    AssistantInput, AssistantOrchestrator = orchestrator_symbols
    from app.agents.intent_router import IntentResult

    seen_payment_types: list[str] = []

    def fake_apply_manual_payment_update(**kwargs):
        seen_payment_types.append(kwargs["payment_type"])
        return SimpleNamespace(
            ok=True,
            requires_confirmation=True,
            member_name="박민서",
            payment_type=kwargs["payment_type"],
            activity_id=str(kwargs["activity_id"]),
            activity_title="테스트 활동",
            required_amount=15000,
            previous_paid_amount=0,
            new_paid_amount=15000,
            previous_status="unpaid",
            new_status="paid",
            payment_record_id=str(uuid4()),
            candidates=None,
            message="박민서님의 활동비 납부 상태를 paid로 변경합니다.",
        )

    proposal = SimpleNamespace(id=uuid4(), status="pending")
    monkeypatch.setattr(
        "app.services.payment_manual_update_service.apply_manual_payment_update",
        fake_apply_manual_payment_update,
    )
    monkeypatch.setattr(
        "app.services.assistant_action_service.create_action_proposal",
        lambda *args, **kwargs: proposal,
    )

    activity_id = uuid4()
    response = AssistantOrchestrator(MagicMock())._payment_manual_update(
        AssistantInput(message="박민서 활동비 완납 처리", activity_id=activity_id),
        IntentResult("payment_manual_update", 0.9, "test"),
        _activity_context(activity_id),
    )

    assert seen_payment_types == ["activity_fee"]
    assert response.result["payment_type"] == "activity_fee"
    assert response.apply_payload == {"action_id": str(proposal.id)}
    assert "활동비" in response.message


def test_global_generic_paid_request_requires_payment_type_confirmation(monkeypatch, orchestrator_symbols):
    AssistantInput, AssistantOrchestrator = orchestrator_symbols
    from app.agents.intent_router import IntentResult

    def fake_apply_manual_payment_update(**kwargs):
        raise AssertionError("global ambiguous request must not update any payment domain")

    monkeypatch.setattr(
        "app.services.payment_manual_update_service.apply_manual_payment_update",
        fake_apply_manual_payment_update,
    )

    response = AssistantOrchestrator(MagicMock())._payment_manual_update(
        AssistantInput(message="박민서 15000원 냈어"),
        IntentResult("payment_manual_update", 0.9, "test"),
        SimpleNamespace(mode="none", activity_id=None, activity_title=None, confidence=0.0, candidates=[]),
    )

    assert response.requires_confirmation is True
    assert response.apply_payload is None
    assert response.result["payment_type"] is None
    assert response.result["needs_payment_type_confirmation"] is True
    assert "회비" in response.message
    assert "활동비" in response.message


def test_manual_payment_update_service_rejects_membership_fee_before_db_lookup():
    from app.services.payment_manual_update_service import apply_manual_payment_update

    db = MagicMock()
    result = apply_manual_payment_update(
        db=db,
        activity_id=uuid4(),
        message="박민서 회비 완납 처리",
        payment_type="membership_fee",
    )

    assert result.ok is False
    assert result.requires_confirmation is True
    assert result.payment_type == "membership_fee"
    assert db.get.called is False
