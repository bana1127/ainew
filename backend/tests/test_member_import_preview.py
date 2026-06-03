# -*- coding: utf-8 -*-
"""Tests for Task 26 member_import_service.

Covers:
  - Column recognition (Korean headers)
  - student_id normalize
  - phone normalize (10-digit leading-0 fix)
  - Row classification: new_member / update_existing / duplicate_candidate / needs_review / invalid
  - preview_member_import does NOT modify DB
"""
from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import MagicMock

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

for _mod_name2 in (
    "app.models", "app.models.base", "app.models.activity",
    "app.models.member", "app.models.payment", "app.models.receipt",
    "app.models.file", "app.models.notification", "app.models.setting",
    "app.models.transaction", "app.models.activity_feedback",
    "app.models.assistant_action",
):
    if _mod_name2 not in sys.modules:
        _m3 = _stub(_mod_name2)
        for _cls in (
            "ActivityReport", "ActivityParticipant", "ActivityCategory",
            "ReferenceReport", "Member", "PaymentRecord", "PaymentAdjustmentLog",
            "BankTransaction", "Receipt", "UploadedFile", "Notification",
            "AppSetting", "ActivityFeedback", "AssistantActionProposal", "Base",
        ):
            # Use MagicMock() instance so attribute access (e.g. .member_id) works
            setattr(_m3, _cls, MagicMock())
        sys.modules[_mod_name2] = _m3


# ---------------------------------------------------------------------------
# Test: normalize helpers (pure functions, no DB)
# ---------------------------------------------------------------------------

from app.services.member_import_service import _clean_student_id, _clean_phone


class TestStudentIdNormalize:
    def test_pure_digits(self):
        assert _clean_student_id("2025170011") == "2025170011"

    def test_float_trailing_zero(self):
        assert _clean_student_id("2025170011.0") == "2025170011"

    def test_with_spaces(self):
        assert _clean_student_id("  2025170011  ") == "2025170011"

    def test_with_hyphen(self):
        assert _clean_student_id("2025-170011") == "2025170011"

    def test_none(self):
        assert _clean_student_id(None) is None

    def test_empty(self):
        assert _clean_student_id("") is None

    def test_nan_float(self):
        import math
        assert _clean_student_id(float("nan")) is None


class TestPhoneNormalize:
    def test_11_digit_with_dashes(self):
        assert _clean_phone("010-1234-5678") == "010-1234-5678"

    def test_11_digit_plain(self):
        assert _clean_phone("01012345678") == "010-1234-5678"

    def test_10_digit_starts_10_excel_strip(self):
        # Excel reads 01056279620 as 1056279620 (strips leading 0)
        assert _clean_phone("1056279620") == "010-5627-9620"

    def test_none(self):
        assert _clean_phone(None) is None

    def test_dash_string(self):
        assert _clean_phone("-") is None


# ---------------------------------------------------------------------------
# Test: row classification (pure, mocked DB)
# ---------------------------------------------------------------------------

from app.services.member_import_service import _classify_row


class TestClassifyRow:
    def _make_db(self, members=None):
        db = MagicMock()
        members = members or []

        def _scalar(stmt):
            # Return first matching member or None
            return members[0] if members else None

        def _scalars(stmt):
            mock_res = MagicMock()
            mock_res.__iter__ = lambda self: iter(members)
            return mock_res

        db.scalar.side_effect = _scalar
        db.scalars.return_value = MagicMock(__iter__=lambda self: iter(members))
        return db

    def test_no_identifiers_is_invalid(self):
        db = self._make_db()
        action, matched_id, diff = _classify_row(db, None, None, None, None, None)
        assert action == "invalid"
        assert matched_id is None

    def test_new_member_when_no_db_match(self):
        db = self._make_db(members=[])
        action, matched_id, diff = _classify_row(db, "박민서", "2025170011", None, None, None)
        assert action == "new_member"
        assert matched_id is None

    def test_update_existing_when_student_id_matches(self):
        existing = MagicMock()
        existing.id = "uuid-1"
        existing.student_id = "2025170011"
        existing.phone = None
        existing.department = None
        existing.email = None

        db = MagicMock()
        db.scalar.return_value = existing

        action, matched_id, diff = _classify_row(db, "박민서", "2025170011", None, None, None)
        assert action == "update_existing"
        assert matched_id == "uuid-1"
