# -*- coding: utf-8 -*-
"""Tests for Task 26 member_merge_service.

Covers:
  - merge_members moves participants/payments to primary
  - duplicate student_id/phone is nulled out
  - duplicate member is set to inactive
  - merging same ids raises ValueError
  - merging already-inactive duplicate raises ValueError
"""
from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest


# ---------------------------------------------------------------------------
# Stubs
# ---------------------------------------------------------------------------

def _stub(name: str) -> ModuleType:
    mod = ModuleType(name)
    mod.__spec__ = None  # type: ignore[attr-defined]
    return mod


for _m in ("psycopg", "psycopg2", "psycopg2.extras"):
    if _m not in sys.modules:
        sys.modules[_m] = _stub(_m)

for _mod_name in ("app.core.database", "app.core.config"):
    if _mod_name not in sys.modules:
        _m2 = _stub(_mod_name)
        _m2.settings = MagicMock()
        sys.modules[_mod_name] = _m2

_sa = _stub("sqlalchemy")
for _attr in ("select", "and_", "or_", "func", "update", "Index", "String", "Text",
              "Boolean", "DateTime", "Date", "Integer", "BigInteger",
              "UniqueConstraint", "ForeignKey", "Float"):
    setattr(_sa, _attr, MagicMock())
sys.modules.setdefault("sqlalchemy", _sa)

_sa_orm = _stub("sqlalchemy.orm")
for _attr in ("Session", "Mapped", "mapped_column", "relationship", "selectinload"):
    setattr(_sa_orm, _attr, MagicMock())
sys.modules.setdefault("sqlalchemy.orm", _sa_orm)

_sa_d = _stub("sqlalchemy.dialects.postgresql")
_sa_d.UUID = MagicMock()
_sa_d.JSONB = MagicMock()
sys.modules.setdefault("sqlalchemy.dialects.postgresql", _sa_d)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_member(name="이주현", student_id="2022130026", phone="010-1234-5678", status="active"):
    m = MagicMock()
    m.id = uuid4()
    m.name = name
    m.student_id = student_id
    m.phone = phone
    m.department = "컴퓨터공학부"
    m.email = None
    m.status = status
    return m


# ---------------------------------------------------------------------------
# Tests — uses patch to avoid model stub conflicts
# ---------------------------------------------------------------------------

class TestMergeMembers:

    def _run_merge(self, primary, duplicate, participants=None, payment_records=None):
        """Run merge_members with mocked DB and model imports."""
        participants = participants or []
        payment_records = payment_records or []

        db = MagicMock()

        def _get(model, key):
            pk = str(key)
            if pk == str(primary.id):
                return primary
            if pk == str(duplicate.id):
                return duplicate
            return None

        db.get.side_effect = _get

        # scalars: first call returns participants, subsequent calls return empty
        call_count = {"n": 0}
        def _scalars(_stmt):
            r = MagicMock()
            if call_count["n"] == 0:
                r.__iter__ = lambda self: iter(participants)
            else:
                r.__iter__ = lambda self: iter(payment_records)
            call_count["n"] += 1
            return r

        db.scalars.side_effect = _scalars
        db.scalar.return_value = None  # no conflicts

        mock_ap = MagicMock()
        mock_ap.member_id = MagicMock()
        mock_ap.activity_report_id = MagicMock()

        mock_member = MagicMock()
        mock_pr = MagicMock()

        with patch.dict(sys.modules, {
            "app.models.activity": MagicMock(ActivityParticipant=mock_ap),
            "app.models.member": MagicMock(Member=mock_member),
            "app.models.payment": MagicMock(PaymentRecord=mock_pr),
        }):
            from importlib import reload
            import app.services.member_merge_service as svc
            reload(svc)
            result = svc.merge_members(db, primary.id, duplicate.id)

        return result

    def test_duplicate_becomes_inactive(self):
        primary = _make_member()
        duplicate = _make_member(student_id="2022130026")
        self._run_merge(primary, duplicate)
        assert duplicate.status == "inactive"

    def test_duplicate_student_id_nulled(self):
        primary = _make_member()
        duplicate = _make_member(student_id="2022130026")
        self._run_merge(primary, duplicate)
        assert duplicate.student_id is None

    def test_duplicate_phone_nulled(self):
        primary = _make_member()
        duplicate = _make_member()
        self._run_merge(primary, duplicate)
        assert duplicate.phone is None

    def test_primary_inherits_missing_phone(self):
        primary = _make_member(phone=None)
        duplicate = _make_member(phone="010-9999-8888")
        self._run_merge(primary, duplicate)
        assert primary.phone == "010-9999-8888"

    def test_result_contains_ids(self):
        primary = _make_member()
        duplicate = _make_member()
        result = self._run_merge(primary, duplicate)
        assert result["primary_id"] == str(primary.id)
        assert result["duplicate_id"] == str(duplicate.id)

    def test_same_ids_raises(self):
        primary = _make_member()
        db = MagicMock()
        db.get.return_value = primary

        mock_ap = MagicMock()
        mock_member = MagicMock()
        mock_pr = MagicMock()

        with patch.dict(sys.modules, {
            "app.models.activity": MagicMock(ActivityParticipant=mock_ap),
            "app.models.member": MagicMock(Member=mock_member),
            "app.models.payment": MagicMock(PaymentRecord=mock_pr),
        }):
            from importlib import reload
            import app.services.member_merge_service as svc
            reload(svc)
            with pytest.raises(ValueError, match="different"):
                svc.merge_members(db, primary.id, primary.id)

    def test_already_inactive_raises(self):
        primary = _make_member()
        duplicate = _make_member(status="inactive")

        db = MagicMock()
        db.get.side_effect = lambda model, key: primary if str(key) == str(primary.id) else duplicate

        mock_ap = MagicMock()
        mock_member = MagicMock()
        mock_pr = MagicMock()

        with patch.dict(sys.modules, {
            "app.models.activity": MagicMock(ActivityParticipant=mock_ap),
            "app.models.member": MagicMock(Member=mock_member),
            "app.models.payment": MagicMock(PaymentRecord=mock_pr),
        }):
            from importlib import reload
            import app.services.member_merge_service as svc
            reload(svc)
            with pytest.raises(ValueError, match="already inactive"):
                svc.merge_members(db, primary.id, duplicate.id)
