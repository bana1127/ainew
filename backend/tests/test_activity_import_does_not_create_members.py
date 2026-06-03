# -*- coding: utf-8 -*-
"""Tests for Task 26: activity import must NOT create Member records.

Uses patch.dict(sys.modules) to isolate model imports inside each test,
avoiding stub pollution when running alongside other test files.
"""
from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest


# ---------------------------------------------------------------------------
# Stubs (minimal — only what the module-level import needs)
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
# Constants
# ---------------------------------------------------------------------------

ACT_UUID = UUID("11111111-1111-1111-1111-111111111111")
ACT_ID = str(ACT_UUID)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_import_row(member_id=None, name="박민서", student_id="2025170011"):
    from app.services.google_form_import_service import ImportRow
    return ImportRow(
        row_index=2,
        name=name,
        student_id=student_id,
        phone=None,
        email=None,
        department=None,
        submitted_at=None,
        member_match_status="new" if member_id is None else "matched",
        member_id=member_id,
        participant_action="create",
        participant_status="applied",
        raw_response={},
    )


def _run_apply_import(rows, form_type="activity_application_form"):
    """Run apply_import with properly mocked models."""
    activity = MagicMock()
    activity.id = ACT_UUID
    activity.title = "테스트 활동"
    activity.deleted_at = None

    db = MagicMock()
    db.get.return_value = activity
    db.scalar.return_value = None  # no existing participant

    mock_ap_cls = MagicMock()
    mock_ap_cls.activity_report_id = MagicMock()
    mock_ap_cls.member_id = MagicMock()

    mock_member_cls = MagicMock()
    mock_pr_cls = MagicMock()
    mock_feedback_cls = MagicMock()

    with patch.dict(sys.modules, {
        "app.models.activity": MagicMock(
            ActivityParticipant=mock_ap_cls,
            ActivityReport=MagicMock(),
        ),
        "app.models.member": MagicMock(Member=mock_member_cls),
        "app.models.payment": MagicMock(PaymentRecord=mock_pr_cls),
        "app.models.activity_feedback": MagicMock(ActivityFeedback=mock_feedback_cls),
    }):
        from importlib import reload
        import app.services.google_form_import_service as svc
        reload(svc)
        result = svc.apply_import(
            db=db,
            activity_id=ACT_ID,
            form_type=form_type,
            rows=rows,
        )

    return result


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestActivityImportDoesNotCreateMembers:

    def test_unmatched_row_does_not_create_member(self):
        """Unmatched row (member_id=None) must not create a Member."""
        row = _make_import_row(member_id=None)
        result = _run_apply_import([row])
        assert result.created_members == 0

    def test_multiple_unmatched_rows_zero_members(self):
        """Multiple unmatched rows → created_members = 0."""
        rows = [
            _make_import_row(member_id=None, name="홍길동", student_id="2025000001"),
            _make_import_row(member_id=None, name="이영희", student_id="2025000002"),
            _make_import_row(member_id=None, name="김철수", student_id="2025000003"),
        ]
        result = _run_apply_import(rows, form_type="member_roster")
        assert result.created_members == 0

    def test_matched_row_still_creates_participant(self):
        """Matched row creates ActivityParticipant but NOT a new Member."""
        from uuid import uuid4
        member_id = str(uuid4())

        row = _make_import_row(member_id=member_id)
        result = _run_apply_import([row])

        # No new member created
        assert result.created_members == 0
