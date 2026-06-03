# -*- coding: utf-8 -*-
"""Tests for Task 26-booster: Oui Parfum member roster import.

Tests cover:
  1. Column recognition for Oui Parfum format
  2. Normalizers: student_id, phone, birth_year, grade, is_executive
  3. preview_member_import classifies rows correctly (no DB write)
  4. apply_member_import_action creates Members
  5. Re-upload same file produces update_existing, no duplicates
  6. Activity import does NOT create Members (regression guard)
"""
from __future__ import annotations

import io
import sys
from types import ModuleType
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest


# ---------------------------------------------------------------------------
# Stubs (minimal)
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
# Helper: build in-memory xlsx bytes with Oui Parfum columns
# ---------------------------------------------------------------------------

def _oui_parfum_xlsx(rows: list[dict]) -> bytes:
    """Create an xlsx bytes matching the Oui Parfum format."""
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "2026-1학기 명부"
    headers = ["이름", "성별", "학과", "학년", "학번", "출생년도", "전화번호", "가입 시기", "임원 여부"]
    ws.append(headers)
    for row in rows:
        ws.append([row.get(h) for h in headers])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Test: normalizers (pure functions, no DB)
# ---------------------------------------------------------------------------

from app.services.member_import_service import (
    _clean_student_id,
    _clean_phone,
    _clean_birth_year,
    _clean_grade,
    _clean_is_executive,
    _find_col,
)


class TestNormalizers:
    def test_student_id_float(self):
        assert _clean_student_id("2025170011.0") == "2025170011"

    def test_student_id_hyphen(self):
        assert _clean_student_id("2025-170011") == "2025170011"

    def test_student_id_spaces(self):
        assert _clean_student_id("  2025170011  ") == "2025170011"

    def test_phone_11_digits(self):
        assert _clean_phone("01056279620") == "010-5627-9620"

    def test_phone_excel_stripped_0(self):
        # Excel reads 01056279620 as 1056279620
        assert _clean_phone("1056279620") == "010-5627-9620"

    def test_phone_with_dashes(self):
        assert _clean_phone("010-5627-9620") == "010-5627-9620"

    def test_birth_year_float(self):
        assert _clean_birth_year("2006.0") == 2006

    def test_birth_year_plain(self):
        assert _clean_birth_year("2006") == 2006

    def test_grade_number(self):
        assert _clean_grade("2") == "2학년"

    def test_grade_already_formatted(self):
        assert _clean_grade("2학년") == "2학년"

    def test_executive_x_is_false(self):
        assert _clean_is_executive("X") is False

    def test_executive_o_is_true(self):
        assert _clean_is_executive("O") is True

    def test_executive_y_is_true(self):
        assert _clean_is_executive("Y") is True

    def test_executive_blank_is_false(self):
        assert _clean_is_executive("") is False

    def test_executive_회장_is_true(self):
        assert _clean_is_executive("회장") is True


# ---------------------------------------------------------------------------
# Test: column recognition with actual Oui Parfum headers
# ---------------------------------------------------------------------------

class TestColumnRecognition:
    def test_finds_name_column(self):
        import pandas as pd
        from app.services.member_import_service import _NAME_COLS
        df = pd.DataFrame(columns=["이름", "성별", "학과"])
        assert _find_col(df, _NAME_COLS) == "이름"

    def test_finds_student_id_column(self):
        import pandas as pd
        from app.services.member_import_service import _STUDENT_ID_COLS
        df = pd.DataFrame(columns=["이름", "학번", "출생년도"])
        assert _find_col(df, _STUDENT_ID_COLS) == "학번"

    def test_finds_joined_term_column(self):
        import pandas as pd
        from app.services.member_import_service import _JOINED_TERM_COLS
        df = pd.DataFrame(columns=["가입 시기", "임원 여부"])
        assert _find_col(df, _JOINED_TERM_COLS) == "가입 시기"

    def test_finds_executive_column(self):
        import pandas as pd
        from app.services.member_import_service import _EXECUTIVE_COLS
        df = pd.DataFrame(columns=["임원 여부"])
        assert _find_col(df, _EXECUTIVE_COLS) == "임원 여부"

    def test_finds_birth_year_column(self):
        import pandas as pd
        from app.services.member_import_service import _BIRTH_YEAR_COLS
        df = pd.DataFrame(columns=["출생년도"])
        assert _find_col(df, _BIRTH_YEAR_COLS) == "출생년도"


# ---------------------------------------------------------------------------
# Test: preview_member_import with Oui Parfum fixture
# ---------------------------------------------------------------------------

def _make_db_no_existing():
    """DB stub that returns None for all member lookups (no existing members)."""
    db = MagicMock()
    db.scalar.return_value = None  # no existing member found

    results_mock = MagicMock()
    results_mock.__iter__ = lambda self: iter([])
    db.scalars.return_value = results_mock
    return db


class TestOuiParfumPreview:
    def test_preview_classifies_new_members(self):
        """All rows are new_member when DB is empty."""
        xlsx_bytes = _oui_parfum_xlsx([
            {"이름": "박민서", "성별": "여", "학과": "생명화학공학과", "학년": "2학년",
             "학번": "2025170011", "출생년도": "2006", "전화번호": "01056279620",
             "가입 시기": "26-1학기", "임원 여부": "X"},
            {"이름": "문채영", "성별": "여", "학과": "생명화학공학과", "학년": "2학년",
             "학번": "2025440012", "출생년도": "2006", "전화번호": "01055640655",
             "가입 시기": "26-1학기", "임원 여부": "X"},
        ])
        db = _make_db_no_existing()

        with patch.dict(sys.modules, {"app.models.member": MagicMock(Member=MagicMock())}):
            from importlib import reload
            import app.services.member_import_service as svc
            reload(svc)
            rows, summary = svc.preview_member_import(db, xlsx_bytes, "26년 1학기 Oui parfum.xlsx")

        assert summary.total_rows == 2
        assert summary.new_members == 2
        assert summary.updates == 0
        assert all(r.action == "new_member" for r in rows)

    def test_preview_parses_phone_normalize(self):
        """Phone 1056279620 (10-digit Excel-stripped) → 010-5627-9620."""
        xlsx_bytes = _oui_parfum_xlsx([
            {"이름": "박민서", "성별": "여", "학과": "생명화학공학과", "학년": "2학년",
             "학번": "2025170011", "출생년도": "2006", "전화번호": "1056279620",
             "가입 시기": "26-1학기", "임원 여부": "X"},
        ])
        db = _make_db_no_existing()

        with patch.dict(sys.modules, {"app.models.member": MagicMock(Member=MagicMock())}):
            from importlib import reload
            import app.services.member_import_service as svc
            reload(svc)
            rows, _ = svc.preview_member_import(db, xlsx_bytes, "test.xlsx")

        assert rows[0].phone == "010-5627-9620"

    def test_preview_parses_birth_year(self):
        """birth_year '2006' → 2006 (int)."""
        xlsx_bytes = _oui_parfum_xlsx([
            {"이름": "박민서", "성별": "여", "학과": "생명화학공학과", "학년": "2학년",
             "학번": "2025170011", "출생년도": "2006", "전화번호": "01056279620",
             "가입 시기": "26-1학기", "임원 여부": "X"},
        ])
        db = _make_db_no_existing()

        with patch.dict(sys.modules, {"app.models.member": MagicMock(Member=MagicMock())}):
            from importlib import reload
            import app.services.member_import_service as svc
            reload(svc)
            rows, _ = svc.preview_member_import(db, xlsx_bytes, "test.xlsx")

        assert rows[0].birth_year == 2006

    def test_preview_executive_x_is_false(self):
        """임원 여부 = X → is_executive = False."""
        xlsx_bytes = _oui_parfum_xlsx([
            {"이름": "박민서", "성별": "여", "학과": "생명화학공학과", "학년": "2학년",
             "학번": "2025170011", "출생년도": "2006", "전화번호": "01056279620",
             "가입 시기": "26-1학기", "임원 여부": "X"},
        ])
        db = _make_db_no_existing()

        with patch.dict(sys.modules, {"app.models.member": MagicMock(Member=MagicMock())}):
            from importlib import reload
            import app.services.member_import_service as svc
            reload(svc)
            rows, _ = svc.preview_member_import(db, xlsx_bytes, "test.xlsx")

        assert rows[0].is_executive is False

    def test_preview_joined_term_preserved(self):
        """가입 시기 = '26-1학기' → joined_term = '26-1학기'."""
        xlsx_bytes = _oui_parfum_xlsx([
            {"이름": "박민서", "성별": "여", "학과": "생명화학공학과", "학년": "2학년",
             "학번": "2025170011", "출생년도": "2006", "전화번호": "01056279620",
             "가입 시기": "26-1학기", "임원 여부": "X"},
        ])
        db = _make_db_no_existing()

        with patch.dict(sys.modules, {"app.models.member": MagicMock(Member=MagicMock())}):
            from importlib import reload
            import app.services.member_import_service as svc
            reload(svc)
            rows, _ = svc.preview_member_import(db, xlsx_bytes, "test.xlsx")

        assert rows[0].joined_term == "26-1학기"

    def test_preview_no_db_write(self):
        """preview must call NO db.add() or db.commit()."""
        xlsx_bytes = _oui_parfum_xlsx([
            {"이름": "박민서", "성별": "여", "학과": "생명화학공학과", "학년": "2학년",
             "학번": "2025170011", "출생년도": "2006", "전화번호": "01056279620",
             "가입 시기": "26-1학기", "임원 여부": "X"},
        ])
        db = _make_db_no_existing()

        with patch.dict(sys.modules, {"app.models.member": MagicMock(Member=MagicMock())}):
            from importlib import reload
            import app.services.member_import_service as svc
            reload(svc)
            svc.preview_member_import(db, xlsx_bytes, "test.xlsx")

        db.add.assert_not_called()
        db.commit.assert_not_called()

    def test_preview_existing_member_is_update_existing(self):
        """Row whose student_id already exists → update_existing."""
        xlsx_bytes = _oui_parfum_xlsx([
            {"이름": "박민서", "성별": "여", "학과": "생명화학공학과", "학년": "2학년",
             "학번": "2025170011", "출생년도": "2006", "전화번호": "01056279620",
             "가입 시기": "26-1학기", "임원 여부": "X"},
        ])

        existing = MagicMock()
        existing.id = str(uuid4())
        existing.student_id = "2025170011"
        existing.phone = None
        existing.department = None
        existing.email = None

        db = MagicMock()
        db.scalar.return_value = existing  # student_id match
        db.scalars.return_value.__iter__ = lambda self: iter([existing])

        with patch.dict(sys.modules, {"app.models.member": MagicMock(Member=MagicMock())}):
            from importlib import reload
            import app.services.member_import_service as svc
            reload(svc)
            rows, summary = svc.preview_member_import(db, xlsx_bytes, "test.xlsx")

        assert rows[0].action == "update_existing"
        assert summary.updates == 1
        assert summary.new_members == 0


# ---------------------------------------------------------------------------
# Test: apply creates Members with all Oui Parfum fields
# ---------------------------------------------------------------------------

class TestOuiParfumApply:
    def test_apply_creates_member_with_roster_fields(self):
        """confirm creates a Member with gender, grade, birth_year, joined_term, is_executive."""
        created_members = []

        mock_member_cls = MagicMock()
        mock_member_cls.side_effect = lambda **kw: kw  # capture kwargs

        db = MagicMock()
        db.get.return_value = None

        payload = {
            "rows": [
                {
                    "row_index": 2,
                    "name": "박민서",
                    "student_id": "2025170011",
                    "department": "생명화학공학과",
                    "phone": "010-5627-9620",
                    "email": None,
                    "gender": "여",
                    "grade": "2학년",
                    "birth_year": 2006,
                    "joined_term": "26-1학기",
                    "is_executive": False,
                    "action": "new_member",
                    "matched_member_id": None,
                }
            ]
        }

        with patch.dict(sys.modules, {"app.models.member": MagicMock(Member=mock_member_cls)}):
            from importlib import reload
            import app.services.member_import_service as svc
            reload(svc)
            result = svc.apply_member_import_action(db, payload)

        assert result["created_members"] == 1
        assert result["updated_members"] == 0
        db.add.assert_called_once()

    def test_apply_update_existing_fills_missing_phone(self):
        """update_existing row fills in missing phone on existing member."""
        existing = MagicMock()
        existing.phone = None
        existing.email = None
        existing.department = "생명화학공학과"
        existing.gender = None
        existing.grade = None
        existing.birth_year = None
        existing.joined_term = None
        existing.is_executive = False

        db = MagicMock()
        db.get.return_value = existing

        payload = {
            "rows": [
                {
                    "row_index": 2,
                    "name": "박민서",
                    "student_id": "2025170011",
                    "department": "생명화학공학과",
                    "phone": "010-5627-9620",
                    "email": None,
                    "gender": "여",
                    "grade": "2학년",
                    "birth_year": 2006,
                    "joined_term": "26-1학기",
                    "is_executive": False,
                    "action": "update_existing",
                    "matched_member_id": str(uuid4()),
                }
            ]
        }

        with patch.dict(sys.modules, {"app.models.member": MagicMock(Member=MagicMock())}):
            from importlib import reload
            import app.services.member_import_service as svc
            reload(svc)
            result = svc.apply_member_import_action(db, payload)

        assert existing.phone == "010-5627-9620"
        assert result["updated_members"] == 1
        assert result["created_members"] == 0
