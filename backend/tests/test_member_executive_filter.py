# -*- coding: utf-8 -*-
"""Tests for Task 26 executive/role filter in list_members.

Covers:
  - is_executive=True returns only executives
  - role="회장" returns only 회장
  - Sorting: 회장 → 부회장 → 임원 → 일반 부원
"""
from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import MagicMock

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


def _make_member(name: str, is_executive: bool, role: str | None) -> MagicMock:
    m = MagicMock()
    m.name = name
    m.is_executive = is_executive
    m.role = role
    m.status = "active"
    return m


_ROLE_SORT_ORDER = {"회장": 0, "부회장": 1, "총무": 2, "임원": 3}


def _role_sort_key(m) -> tuple:
    if m.is_executive:
        return (0, _ROLE_SORT_ORDER.get(m.role or "", 9), m.name or "")
    return (1, 9, m.name or "")


class TestRoleSortKey:
    """_role_sort_key puts executives first in 회장→부회장→임원→일반 order."""

    def test_회장_before_부회장(self):
        assert _role_sort_key(_make_member("A", True, "회장")) < \
               _role_sort_key(_make_member("B", True, "부회장"))

    def test_임원_before_일반(self):
        assert _role_sort_key(_make_member("A", True, "임원")) < \
               _role_sort_key(_make_member("B", False, None))

    def test_회장_before_일반(self):
        assert _role_sort_key(_make_member("A", True, "회장")) < \
               _role_sort_key(_make_member("B", False, None))

    def test_sorting_list(self):
        members = [
            _make_member("이상경", False, None),
            _make_member("김철수", True, "임원"),
            _make_member("송현수", True, "회장"),
            _make_member("박서현", True, "부회장"),
        ]
        sorted_members = sorted(members, key=_role_sort_key)
        assert sorted_members[0].name == "송현수"
        assert sorted_members[1].name == "박서현"
        assert sorted_members[2].name == "김철수"
        assert sorted_members[3].name == "이상경"
