from __future__ import annotations

import sys
from types import ModuleType
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pandas as pd
import pytest


def _stub(name: str) -> ModuleType:
    mod = ModuleType(name)
    mod.__spec__ = None  # type: ignore[attr-defined]
    return mod


class _Column:
    def __eq__(self, other):  # noqa: D105
        return ("eq", other)

    def is_(self, other):
        return ("is", other)

    def in_(self, other):
        return ("in", other)


class _Select:
    def where(self, *args, **kwargs):
        return self


def _select(*args, **kwargs):
    return _Select()


def _and_(*args, **kwargs):
    return ("and", args)


_sa = _stub("sqlalchemy")
_sa.select = _select  # type: ignore[attr-defined]
_sa.and_ = _and_  # type: ignore[attr-defined]
sys.modules.setdefault("sqlalchemy", _sa)

_sa_orm = _stub("sqlalchemy.orm")
_sa_orm.Session = object  # type: ignore[attr-defined]
sys.modules.setdefault("sqlalchemy.orm", _sa_orm)


class ActivityReport:
    def __init__(self, **kwargs):
        self.id = kwargs.pop("id", uuid4())
        for key, value in kwargs.items():
            setattr(self, key, value)


class ActivityParticipant:
    activity_report_id = _Column()
    member_id = _Column()
    external_name = _Column()
    external_student_id = _Column()

    def __init__(self, **kwargs):
        self.id = uuid4()
        for key, value in kwargs.items():
            setattr(self, key, value)


class Member:
    student_id = _Column()
    phone = _Column()
    name = _Column()
    department = _Column()

    def __init__(self, **kwargs):
        self.id = kwargs.pop("id", uuid4())
        for key, value in kwargs.items():
            setattr(self, key, value)


class UploadedFile:
    id = _Column()


class AssistantActionProposal:
    pass


_models_pkg = sys.modules.setdefault("app.models", _stub("app.models"))
_activity_mod = sys.modules.setdefault("app.models.activity", _stub("app.models.activity"))
_member_mod = sys.modules.setdefault("app.models.member", _stub("app.models.member"))
_file_mod = sys.modules.setdefault("app.models.file", _stub("app.models.file"))
_action_mod = sys.modules.setdefault("app.models.assistant_action", _stub("app.models.assistant_action"))
_payment_mod = sys.modules.setdefault("app.models.payment", _stub("app.models.payment"))
_transaction_mod = sys.modules.setdefault("app.models.transaction", _stub("app.models.transaction"))
_setting_mod = sys.modules.setdefault("app.models.setting", _stub("app.models.setting"))

_models_pkg.ActivityReport = ActivityReport  # type: ignore[attr-defined]
_models_pkg.ActivityParticipant = ActivityParticipant  # type: ignore[attr-defined]
_models_pkg.Member = Member  # type: ignore[attr-defined]
_models_pkg.UploadedFile = UploadedFile  # type: ignore[attr-defined]
_models_pkg.AssistantActionProposal = AssistantActionProposal  # type: ignore[attr-defined]
_models_pkg.BankTransaction = MagicMock  # type: ignore[name-defined,attr-defined]
_models_pkg.PaymentRecord = MagicMock  # type: ignore[name-defined,attr-defined]
_activity_mod.ActivityReport = ActivityReport  # type: ignore[attr-defined]
_activity_mod.ActivityParticipant = ActivityParticipant  # type: ignore[attr-defined]
_member_mod.Member = Member  # type: ignore[attr-defined]
_file_mod.UploadedFile = UploadedFile  # type: ignore[attr-defined]
_action_mod.AssistantActionProposal = AssistantActionProposal  # type: ignore[attr-defined]
_payment_mod.PaymentRecord = MagicMock  # type: ignore[name-defined,attr-defined]
_payment_mod.PaymentAdjustmentLog = MagicMock  # type: ignore[name-defined,attr-defined]
_transaction_mod.BankTransaction = MagicMock  # type: ignore[name-defined,attr-defined]
_setting_mod.AppSetting = MagicMock  # type: ignore[name-defined,attr-defined]


@pytest.fixture(autouse=True)
def _install_model_stubs():
    models_pkg = sys.modules.setdefault("app.models", _stub("app.models"))
    activity_mod = sys.modules.setdefault("app.models.activity", _stub("app.models.activity"))
    member_mod = sys.modules.setdefault("app.models.member", _stub("app.models.member"))
    file_mod = sys.modules.setdefault("app.models.file", _stub("app.models.file"))
    action_mod = sys.modules.setdefault("app.models.assistant_action", _stub("app.models.assistant_action"))
    payment_mod = sys.modules.setdefault("app.models.payment", _stub("app.models.payment"))
    transaction_mod = sys.modules.setdefault("app.models.transaction", _stub("app.models.transaction"))
    setting_mod = sys.modules.setdefault("app.models.setting", _stub("app.models.setting"))

    models_pkg.ActivityReport = ActivityReport  # type: ignore[attr-defined]
    models_pkg.ActivityParticipant = ActivityParticipant  # type: ignore[attr-defined]
    models_pkg.Member = Member  # type: ignore[attr-defined]
    models_pkg.UploadedFile = UploadedFile  # type: ignore[attr-defined]
    models_pkg.AssistantActionProposal = AssistantActionProposal  # type: ignore[attr-defined]
    models_pkg.BankTransaction = MagicMock  # type: ignore[name-defined,attr-defined]
    models_pkg.PaymentRecord = MagicMock  # type: ignore[name-defined,attr-defined]
    activity_mod.ActivityReport = ActivityReport  # type: ignore[attr-defined]
    activity_mod.ActivityParticipant = ActivityParticipant  # type: ignore[attr-defined]
    member_mod.Member = Member  # type: ignore[attr-defined]
    file_mod.UploadedFile = UploadedFile  # type: ignore[attr-defined]
    action_mod.AssistantActionProposal = AssistantActionProposal  # type: ignore[attr-defined]
    payment_mod.PaymentRecord = MagicMock  # type: ignore[name-defined,attr-defined]
    payment_mod.PaymentAdjustmentLog = MagicMock  # type: ignore[name-defined,attr-defined]
    transaction_mod.BankTransaction = MagicMock  # type: ignore[name-defined,attr-defined]
    setting_mod.AppSetting = MagicMock  # type: ignore[name-defined,attr-defined]


def test_intent_router_detects_participant_import_for_spreadsheet():
    from app.agents.intent_router import route

    result = route(
        message="이 활동 참가자 추가해줘",
        file_names=["participants.xlsx"],
    )

    assert result.intent == "participant_import"


def test_preview_matched_member_creates_pending_proposal(monkeypatch):
    from app.services import activity_participant_import_service as svc

    activity_id = uuid4()
    member_id = uuid4()
    member = SimpleNamespace(
        id=member_id,
        name="박민서",
        student_id="2025170011",
        phone="010-1234-5678",
        department="경영학과",
    )
    db = SimpleNamespace(
        get=lambda model, obj_id: SimpleNamespace(id=activity_id, title="조향 활동"),
        scalar=lambda stmt: member if not hasattr(db, "_member_seen") else None,
        scalars=lambda stmt: [],
    )

    def scalar(stmt):
        if not hasattr(db, "_member_seen"):
            db._member_seen = True
            return member
        return None

    db.scalar = scalar
    monkeypatch.setattr(
        svc,
        "_read_file",
        lambda file_bytes, filename: pd.DataFrame(
            [{"이름": "박민서", "학번": "2025170011", "학과": "경영학과", "메모": "신청"}]
        ),
    )
    monkeypatch.setattr(
        "app.services.assistant_action_service.create_action_proposal",
        lambda *args, **kwargs: SimpleNamespace(id=uuid4()),
    )

    preview = svc.preview_participant_import(
        db=db,
        file_bytes=b"ignored",
        filename="participants.xlsx",
        activity_id=activity_id,
    )

    assert preview.requires_confirmation is True
    assert preview.summary.matched_members == 1
    assert preview.summary.will_create_participants == 1
    assert preview.rows[0].action == "link_existing_member"
    assert preview.rows[0].matched_member_id == str(member_id)


def test_preview_unregistered_candidate_requires_user_selection(monkeypatch):
    from app.services import activity_participant_import_service as svc

    activity_id = uuid4()
    db = SimpleNamespace(
        get=lambda model, obj_id: SimpleNamespace(id=activity_id, title="조향 활동"),
        scalar=lambda stmt: None,
        scalars=lambda stmt: [],
    )
    monkeypatch.setattr(
        svc,
        "_read_file",
        lambda file_bytes, filename: pd.DataFrame(
            [{"이름": "외부참가자", "학번": "9999999999", "학과": "외부 기관"}]
        ),
    )
    monkeypatch.setattr(
        "app.services.assistant_action_service.create_action_proposal",
        lambda *args, **kwargs: SimpleNamespace(id=uuid4()),
    )

    preview = svc.preview_participant_import(
        db=db,
        file_bytes=b"ignored",
        filename="participants.xlsx",
        activity_id=activity_id,
    )

    row = preview.rows[0]
    assert preview.summary.unregistered_candidates == 1
    assert row.action == "needs_user_selection"
    assert "create_new_member" in row.available_actions
    assert "mark_external" in row.available_actions


def test_confirm_mark_external_creates_external_participant():
    from app.services.activity_participant_import_service import confirm_participant_import

    activity_id = uuid4()
    action_id = uuid4()
    proposal = SimpleNamespace(
        id=action_id,
        status="pending",
        payload_json={
            "activity_id": str(activity_id),
            "file_id": None,
            "rows": [
                {
                    "row_index": 2,
                    "name": "외부참가자",
                    "student_id": "9999999999",
                    "department": "외부 기관",
                    "phone": None,
                    "match_status": "unregistered_candidate",
                    "matched_member_id": None,
                    "participant_status": "needs_review",
                    "action": "needs_user_selection",
                    "available_actions": ["create_new_member", "mark_external", "ignore"],
                    "reason": "매칭되는 부원 없음",
                    "raw_response": {"비고": "외부 초청"},
                }
            ],
        },
        preview_json={},
        confirmed_at=None,
        applied_at=None,
    )
    added = []

    def get(model, obj_id):
        if getattr(model, "__name__", "") == "AssistantActionProposal":
            return proposal
        if getattr(model, "__name__", "") == "ActivityReport":
            return SimpleNamespace(id=activity_id, title="조향 활동")
        return None

    db = SimpleNamespace(
        get=get,
        scalar=lambda stmt: None,
        add=lambda obj: added.append(obj),
        flush=lambda: None,
        commit=lambda: None,
    )

    result = confirm_participant_import(
        db=db,
        action_id=action_id,
        row_overrides=[{"row_index": 2, "selected_action": "mark_external"}],
    )

    assert result.created_participants == 1
    assert result.external_participants == 1
    assert proposal.status == "applied"
    participant = added[0]
    assert participant.member_id is None
    assert participant.external_name == "외부참가자"
    assert participant.external_affiliation == "외부 기관"
    assert participant.external_student_id == "9999999999"


def test_common_confirm_passes_participant_import_action_id(monkeypatch):
    from app.services import assistant_action_service as svc

    action_id = uuid4()
    proposal = SimpleNamespace(
        id=action_id,
        action_type="participant_import",
        status="pending",
        payload_json={"activity_id": str(uuid4()), "rows": []},
        preview_json={},
        confirmed_at=None,
        applied_at=None,
    )
    db = SimpleNamespace(
        get=lambda model, obj_id: proposal,
        commit=lambda: None,
        refresh=lambda obj: None,
    )
    seen = {}

    def fake_apply(db_arg, payload):
        seen["payload"] = payload
        assert proposal.status == "pending"
        return {"ok": True}

    monkeypatch.setattr(svc, "apply_participant_import_action", fake_apply)

    _, result = svc.confirm_action_proposal(db, action_id)

    assert result == {"ok": True}
    assert seen["payload"]["action_id"] == str(action_id)
    assert proposal.status == "applied"
