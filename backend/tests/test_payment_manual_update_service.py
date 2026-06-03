# -*- coding: utf-8 -*-
"""Tests for payment_manual_update_service pure functions.

Integration tests (apply_manual_payment_update) require a live DB session,
so they are covered by the E2E test suite.  This file focuses on pure
parsing/calculation logic that has no external dependencies.
"""
from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest


# ---------------------------------------------------------------------------
# Stub heavy DB/ORM imports so the module can load without psycopg / SA
# ---------------------------------------------------------------------------

def _stub(name: str) -> ModuleType:
    mod = ModuleType(name)
    mod.__spec__ = None  # type: ignore[attr-defined]
    return mod


for _m in ("psycopg", "psycopg2", "psycopg2.extras"):
    if _m not in sys.modules:
        sys.modules[_m] = _stub(_m)

_db_mod = _stub("app.core.database")
_db_mod.Base = MagicMock()  # type: ignore[attr-defined]
_db_mod.engine = MagicMock()  # type: ignore[attr-defined]
_db_mod.SessionLocal = MagicMock()  # type: ignore[attr-defined]
_db_mod.get_db = MagicMock()  # type: ignore[attr-defined]
sys.modules["app.core.database"] = _db_mod

# Stub SQLAlchemy (may not be installed in test venv)
_sa = _stub("sqlalchemy")
_sa.select = MagicMock()  # type: ignore[attr-defined]
_sa.and_ = MagicMock()  # type: ignore[attr-defined]
sys.modules.setdefault("sqlalchemy", _sa)
_sa_orm = _stub("sqlalchemy.orm")
_sa_orm.Session = MagicMock()  # type: ignore[attr-defined]
sys.modules.setdefault("sqlalchemy.orm", _sa_orm)

# Stub model modules to avoid ORM setup
for _mod_name in (
    "app.models.activity",
    "app.models.member",
    "app.models.payment",
):
    if _mod_name not in sys.modules:
        _m2 = _stub(_mod_name)
        _m2.ActivityReport = MagicMock  # type: ignore[attr-defined]
        _m2.ActivityParticipant = MagicMock  # type: ignore[attr-defined]
        _m2.Member = MagicMock  # type: ignore[attr-defined]
        _m2.PaymentRecord = MagicMock  # type: ignore[attr-defined]
        _m2.PaymentAdjustmentLog = MagicMock  # type: ignore[attr-defined]
        sys.modules[_mod_name] = _m2

# Only import the pure functions (no DB interaction)
from app.services.payment_manual_update_service import (  # noqa: E402
    apply_manual_payment_update,
    extract_member_name,
    parse_payment_amount,
    _recalculate_status,
)


# ============================================================
# extract_member_name
# ============================================================

class TestExtractMemberName:
    def test_suffix_haksaeng(self):
        name = extract_member_name(
            "박민서 학생이 활동비 15000원을 납부 했으니"
        )
        assert name == "박민서"  # 박민서

    def test_suffix_nim(self):
        name = extract_member_name("김가은님 납부 처리해줘")
        assert name == "김가은"  # 김가은

    def test_suffix_bowon(self):
        name = extract_member_name("이지우 부원이 됩어")
        assert name == "이지우"  # 이지우

    def test_returns_none_for_keyword_only(self):
        # "활동비 납부 완료로 바꿔줘" has no member name
        result = extract_member_name(
            "활동비 납부 완료로 바꿈줘"
        )
        # Should not return a common noun
        assert result not in ("활동비", "납부", "완료")


# ============================================================
# parse_payment_amount
# ============================================================

class TestParsePaymentAmount:
    def test_plain_number(self):
        assert parse_payment_amount("15000원을 납부했어") == 15000

    def test_comma_number(self):
        assert parse_payment_amount("15,000원 냈어") == 15000

    def test_man_won(self):
        assert parse_payment_amount("만원 냈어") == 10000

    def test_1_man_won(self):
        assert parse_payment_amount("1만원 냈어") == 10000

    def test_2_man_won(self):
        assert parse_payment_amount("2만원 입금했어") == 20000

    def test_1man5cheon(self):
        assert parse_payment_amount("1만5천원") == 15000

    def test_manosucheon(self):
        # "만오천원"
        assert parse_payment_amount("만오천원 납부") == 15000

    def test_no_amount(self):
        assert parse_payment_amount(
            "납부 완료로 바꿈줘"
        ) is None


# ============================================================
# _recalculate_status
# ============================================================

class TestRecalculateStatus:
    def test_zero_is_unpaid(self):
        assert _recalculate_status(0, 15000, "unpaid") == "unpaid"

    def test_full_pay_is_paid(self):
        assert _recalculate_status(15000, 15000, "unpaid") == "paid"

    def test_partial(self):
        assert _recalculate_status(10000, 15000, "unpaid") == "partial"

    def test_overpaid(self):
        assert _recalculate_status(20000, 15000, "unpaid") == "overpaid"

    def test_exempt_preserved(self):
        assert _recalculate_status(0, 15000, "exempt") == "exempt"

    def test_cancelled_preserved(self):
        assert _recalculate_status(15000, 15000, "cancelled") == "cancelled"

    def test_need_check_recalculated(self):
        # need_check is NOT a preserved state — it gets recalculated
        assert _recalculate_status(15000, 15000, "need_check") == "paid"

    def test_partial_then_full(self):
        assert _recalculate_status(15000, 15000, "partial") == "paid"


class _FakeResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class _FakeQuery:
    def __init__(self):
        self.kind = None

    def where(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self


class _FakeDB:
    def __init__(self, activity, participant, member, record):
        self.activity = activity
        self.participant = participant
        self.member = member
        self.record = record
        self.commit_called = False
        self.add_called = False

    def get(self, model, object_id):
        if object_id == self.activity.id:
            return self.activity
        if object_id == self.member.id:
            return self.member
        return None

    def scalars(self, query):
        if getattr(query, "kind", None) == "participant":
            return [self.participant]
        if getattr(query, "kind", None) == "member":
            return [self.member]
        return []

    def execute(self, query):
        if getattr(query, "kind", None) == "payment":
            return _FakeResult(self.record)
        return _FakeResult(None)

    def add(self, _obj):
        self.add_called = True

    def commit(self):
        self.commit_called = True


class TestDryRun:
    def test_dry_run_does_not_mutate_existing_record(self, monkeypatch):
        activity_id = uuid4()
        member_id = uuid4()
        activity = SimpleNamespace(id=activity_id, title="위퍼퓸", deleted_at=None)
        participant = SimpleNamespace(activity_report_id=activity_id, member_id=member_id)
        member = SimpleNamespace(id=member_id, name="박민서", student_id="20230001")
        record = SimpleNamespace(
            id=uuid4(),
            member_id=member_id,
            required_amount=25000,
            paid_amount=0,
            status="unpaid",
        )
        db = _FakeDB(activity, participant, member, record)

        class _ActivityParticipant:
            activity_report_id = object()

        class _ActivityReport:
            __name__ = "ActivityReport"

        class _Member:
            __name__ = "Member"
            id = SimpleNamespace(in_=lambda _ids: object())
            name = object()

        class _PaymentRecord:
            __name__ = "PaymentRecord"
            member_id = object()
            activity_report_id = object()
            period = object()
            payment_type = object()

        class _PaymentAdjustmentLog:
            pass

        activity_mod = sys.modules["app.models.activity"]
        member_mod = sys.modules["app.models.member"]
        payment_mod = sys.modules["app.models.payment"]
        monkeypatch.setattr(activity_mod, "ActivityParticipant", _ActivityParticipant, raising=False)
        monkeypatch.setattr(activity_mod, "ActivityReport", _ActivityReport, raising=False)
        monkeypatch.setattr(member_mod, "Member", _Member, raising=False)
        monkeypatch.setattr(payment_mod, "PaymentRecord", _PaymentRecord, raising=False)
        monkeypatch.setattr(payment_mod, "PaymentAdjustmentLog", _PaymentAdjustmentLog, raising=False)

        def fake_select(model):
            q = _FakeQuery()
            if model is _ActivityParticipant:
                q.kind = "participant"
            elif model is _Member:
                q.kind = "member"
            elif model is _PaymentRecord:
                q.kind = "payment"
            return q

        monkeypatch.setattr("app.services.payment_manual_update_service.select", fake_select)
        monkeypatch.setattr("app.services.payment_manual_update_service.and_", lambda *args: object())

        result = apply_manual_payment_update(
            db=db,
            activity_id=activity_id,
            message="박민서 학생이 활동비 25000원 제출했어",
            dry_run=True,
        )

        assert result.ok is True
        assert result.new_paid_amount == 25000
        assert result.new_status == "paid"
        assert record.paid_amount == 0
        assert record.status == "unpaid"
        assert db.commit_called is False
        assert db.add_called is False
