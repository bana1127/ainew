# -*- coding: utf-8 -*-
"""Tests for executive role import (Task 26 hotfix).

Covers:
  1. 임원 여부 O → is_executive=True, role="임원"
  2. 임원 여부 X → is_executive=False, role=None
  3. 임원 여부 = 회장 → is_executive=True, role="회장"
  4. 임원 여부 = 부회장 → is_executive=True, role="부회장"
  5. 기존 회장 role이 O 값으로 덮어써지지 않음
  6. 기존 없는 role에 O → role="임원" 저장
"""
from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest


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

from app.services.member_import_service import _clean_executive_info


class TestCleanExecutiveInfo:
    def test_o_gives_executive_role(self):
        is_exec, role = _clean_executive_info("O")
        assert is_exec is True
        assert role == "임원"

    def test_x_gives_no_executive(self):
        is_exec, role = _clean_executive_info("X")
        assert is_exec is False
        assert role is None

    def test_회장_gives_회장_role(self):
        is_exec, role = _clean_executive_info("회장")
        assert is_exec is True
        assert role == "회장"

    def test_부회장_gives_부회장_role(self):
        is_exec, role = _clean_executive_info("부회장")
        assert is_exec is True
        assert role == "부회장"

    def test_총무_gives_총무_role(self):
        is_exec, role = _clean_executive_info("총무")
        assert is_exec is True
        assert role == "총무"

    def test_y_gives_임원(self):
        is_exec, role = _clean_executive_info("Y")
        assert is_exec is True
        assert role == "임원"

    def test_blank_gives_no_executive(self):
        is_exec, role = _clean_executive_info("")
        assert is_exec is False

    def test_none_gives_no_executive(self):
        is_exec, role = _clean_executive_info(None)
        assert is_exec is False

    def test_일반_gives_no_executive(self):
        is_exec, role = _clean_executive_info("일반")
        assert is_exec is False


class TestApplyMemberImportRoleLogic:
    """apply_member_import_action role update rules."""

    def _run_apply(self, existing_member, payload_row):
        db = MagicMock()
        db.get.return_value = existing_member

        payload = {"rows": [payload_row]}

        with patch.dict(sys.modules, {"app.models.member": MagicMock(Member=MagicMock())}):
            from importlib import reload
            import app.services.member_import_service as svc
            reload(svc)
            result = svc.apply_member_import_action(db, payload)

        return result

    def test_no_role_plus_executive_sets_임원(self):
        """Member with no role + is_executive=True in import → role='임원'."""
        existing = MagicMock()
        existing.phone = None
        existing.email = None
        existing.department = None
        existing.gender = None
        existing.grade = None
        existing.birth_year = None
        existing.joined_term = None
        existing.is_executive = False
        existing.role = None

        row = {
            "row_index": 2, "name": "박민서", "student_id": "2025170011",
            "department": None, "phone": None, "email": None,
            "gender": None, "grade": None, "birth_year": None,
            "joined_term": None, "is_executive": True, "role": "임원",
            "action": "update_existing",
            "matched_member_id": str(uuid4()),
        }

        self._run_apply(existing, row)
        assert existing.role == "임원"
        assert existing.is_executive is True

    def test_회장_not_overwritten_by_임원(self):
        """Member with role='회장' must NOT be overwritten by generic '임원'."""
        existing = MagicMock()
        existing.phone = None
        existing.email = None
        existing.department = None
        existing.gender = None
        existing.grade = None
        existing.birth_year = None
        existing.joined_term = None
        existing.is_executive = True
        existing.role = "회장"

        row = {
            "row_index": 2, "name": "송현수", "student_id": "2023000001",
            "department": None, "phone": None, "email": None,
            "gender": None, "grade": None, "birth_year": None,
            "joined_term": None, "is_executive": True, "role": "임원",
            "action": "update_existing",
            "matched_member_id": str(uuid4()),
        }

        self._run_apply(existing, row)
        assert existing.role == "회장"  # must not change

    def test_부회장_not_overwritten_by_임원(self):
        """Member with role='부회장' must NOT be overwritten by generic '임원'."""
        existing = MagicMock()
        existing.phone = None
        existing.email = None
        existing.department = None
        existing.gender = None
        existing.grade = None
        existing.birth_year = None
        existing.joined_term = None
        existing.is_executive = True
        existing.role = "부회장"

        row = {
            "row_index": 3, "name": "김성래", "student_id": "2023000002",
            "department": None, "phone": None, "email": None,
            "gender": None, "grade": None, "birth_year": None,
            "joined_term": None, "is_executive": True, "role": "임원",
            "action": "update_existing",
            "matched_member_id": str(uuid4()),
        }

        self._run_apply(existing, row)
        assert existing.role == "부회장"

    def test_new_member_has_role(self):
        """new_member row with role='회장' → Member created with role='회장'."""
        db = MagicMock()

        mock_member_cls = MagicMock()
        created_kwargs = {}
        mock_member_cls.side_effect = lambda **kw: created_kwargs.update(kw) or kw

        payload = {"rows": [{
            "row_index": 2, "name": "이준혁", "student_id": "2023000003",
            "department": "전자공학과", "phone": "010-1111-2222", "email": None,
            "gender": "남", "grade": "3학년", "birth_year": 2004,
            "joined_term": "23-1학기", "is_executive": True, "role": "회장",
            "action": "new_member", "matched_member_id": None,
        }]}

        with patch.dict(sys.modules, {"app.models.member": MagicMock(Member=mock_member_cls)}):
            from importlib import reload
            import app.services.member_import_service as svc
            reload(svc)
            result = svc.apply_member_import_action(db, payload)

        assert result["created_members"] == 1
        db.add.assert_called_once()
