# -*- coding: utf-8 -*-
"""Tests for member deduplication logic.

Covers:
- student_id / phone normalization (pure functions)
- _find_col for complex column names
- DedupeLogic: pure-Python simulation of the migration SQL logic
"""
from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import MagicMock

import pytest


# ---------------------------------------------------------------------------
# Minimal stubs
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
        _m2.Base = MagicMock()  # type: ignore[attr-defined]
        _m2.engine = MagicMock()  # type: ignore[attr-defined]
        _m2.SessionLocal = MagicMock()  # type: ignore[attr-defined]
        _m2.get_db = MagicMock()  # type: ignore[attr-defined]
        _m2.settings = MagicMock()  # type: ignore[attr-defined]
        sys.modules[_mod_name] = _m2

_sa = _stub("sqlalchemy")
_sa.select = MagicMock()  # type: ignore[attr-defined]
_sa.and_ = MagicMock()  # type: ignore[attr-defined]
_sa.func = MagicMock()  # type: ignore[attr-defined]
sys.modules.setdefault("sqlalchemy", _sa)
_sa_orm = _stub("sqlalchemy.orm")
_sa_orm.Session = MagicMock()  # type: ignore[attr-defined]
sys.modules.setdefault("sqlalchemy.orm", _sa_orm)

_pd = _stub("pandas")
_pd.isna = lambda v: False  # type: ignore[attr-defined]
sys.modules.setdefault("pandas", _pd)

for _mod_name2 in (
    "app.services.excel_form_classifier",
):
    if _mod_name2 not in sys.modules:
        _m3 = _stub(_mod_name2)
        _m3.FormClassificationResult = MagicMock  # type: ignore[attr-defined]
        _m3.classify_excel_form = MagicMock()  # type: ignore[attr-defined]
        sys.modules[_mod_name2] = _m3

# Import pure functions only (no models needed)
from app.services.google_form_import_service import (  # noqa: E402
    _clean_student_id,
    _clean_phone,
    _find_col,
)


# ============================================================
# _clean_student_id
# ============================================================

class TestCleanStudentId:
    def test_plain_string(self):
        assert _clean_student_id("2022130026") == "2022130026"

    def test_float_string(self):
        assert _clean_student_id("2022130026.0") == "2022130026"

    def test_float_value(self):
        # Excel reads as 2022130026.0 → str → normalize
        assert _clean_student_id(2022130026.0) == "2022130026"

    def test_leading_trailing_spaces(self):
        assert _clean_student_id("  2022130026  ") == "2022130026"

    def test_with_dashes(self):
        assert _clean_student_id("2022-130026") == "2022130026"

    def test_none(self):
        assert _clean_student_id(None) is None

    def test_empty_string(self):
        assert _clean_student_id("") is None

    def test_pure_alpha_returns_none(self):
        assert _clean_student_id("ABC") is None

    def test_same_after_normalize(self):
        # Two different raw representations should normalize to the same value
        a = _clean_student_id("2022130026")
        b = _clean_student_id("2022130026.0")
        c = _clean_student_id(2022130026.0)
        assert a == b == c


# ============================================================
# _clean_phone
# ============================================================

class TestCleanPhone:
    def test_already_formatted(self):
        assert _clean_phone("010-1234-5678") == "010-1234-5678"

    def test_digits_11(self):
        assert _clean_phone("01012345678") == "010-1234-5678"

    def test_missing_leading_zero_10digits_starts_10(self):
        # 1056279620 → 10 digits, starts with 10 → prepend 0 → 01056279620
        result = _clean_phone("1056279620")
        assert result == "010-5627-9620"

    def test_missing_leading_zero_generic_10(self):
        result = _clean_phone("1012345678")
        assert result == "010-1234-5678"

    def test_none(self):
        assert _clean_phone(None) is None


# ============================================================
# _find_col: student_id column with verbose names
# ============================================================

class TestFindColStudentId:
    def _df(self, columns):
        df = MagicMock()
        df.columns = columns
        return df

    def test_plain(self):
        from app.services.google_form_import_service import _STUDENT_ID_COLS
        df = self._df(["이름", "학번", "연락처"])
        assert _find_col(df, _STUDENT_ID_COLS) == "학번"

    def test_with_prefix_and_parens(self):
        from app.services.google_form_import_service import _STUDENT_ID_COLS
        df = self._df(["이름", "2.학번 ( 끝까지 적어주세요 )", "연락처"])
        assert _find_col(df, _STUDENT_ID_COLS) == "2.학번 ( 끝까지 적어주세요 )"

    def test_space_variant(self):
        from app.services.google_form_import_service import _STUDENT_ID_COLS
        df = self._df(["이름", "2. 학번( 끝까지 써주세요 )", "연락처"])
        assert _find_col(df, _STUDENT_ID_COLS) == "2. 학번( 끝까지 써주세요 )"


# ============================================================
# Dedupe logic simulation (pure Python, no DB)
# Tests the logic that the migration SQL implements.
# ============================================================

from types import SimpleNamespace
from uuid import uuid4


def _simulate_dedupe(members, participants, payment_records):
    """Simulate the migration SQL logic in pure Python.

    Returns (updated_members, updated_participants, updated_payment_records)
    as new lists reflecting post-dedupe state.
    """
    # Sort members: oldest first, then by id
    sorted_members = sorted(
        members,
        key=lambda m: (m.created_at if m.created_at else "", str(m.id)),
    )

    # Find primaries: first occurrence of each student_id
    primary_by_sid: dict[str, object] = {}
    for m in sorted_members:
        if m.student_id and m.student_id not in primary_by_sid:
            primary_by_sid[m.student_id] = m

    # Build dup → primary map
    dup_to_primary: dict = {}
    for m in sorted_members:
        if m.student_id and m.student_id in primary_by_sid:
            primary = primary_by_sid[m.student_id]
            if primary.id != m.id:
                dup_to_primary[m.id] = primary

    # Re-point participants
    new_participants = []
    primary_participant_keys: set = set()
    # First pass: record existing primary participants
    for p in participants:
        if p.member_id not in dup_to_primary:
            primary_participant_keys.add((p.activity_report_id, p.member_id))

    for p in participants:
        if p.member_id in dup_to_primary:
            primary = dup_to_primary[p.member_id]
            key = (p.activity_report_id, primary.id)
            if key not in primary_participant_keys:
                # Move to primary
                new_p = SimpleNamespace(
                    id=p.id,
                    activity_report_id=p.activity_report_id,
                    member_id=primary.id,
                )
                new_participants.append(new_p)
                primary_participant_keys.add(key)
            # else: conflict → drop
        else:
            new_participants.append(p)

    # Re-point payment_records
    new_records = []
    primary_record_keys: set = set()
    for r in payment_records:
        if r.member_id not in dup_to_primary:
            primary_record_keys.add((r.member_id, r.period, r.payment_type))

    for r in payment_records:
        if r.member_id in dup_to_primary:
            primary = dup_to_primary[r.member_id]
            key = (primary.id, r.period, r.payment_type)
            if key not in primary_record_keys:
                new_r = SimpleNamespace(
                    id=r.id, member_id=primary.id,
                    period=r.period, payment_type=r.payment_type,
                )
                new_records.append(new_r)
                primary_record_keys.add(key)
        else:
            new_records.append(r)

    # Soft-delete duplicates AND null their student_id
    new_members = []
    for m in members:
        if m.id in dup_to_primary:
            new_m = SimpleNamespace(
                id=m.id, name=m.name,
                student_id=None,    # ← CRITICAL: must be None after dedupe
                status="inactive",
                created_at=m.created_at,
            )
            new_members.append(new_m)
        else:
            new_members.append(m)

    return new_members, new_participants, new_records


def _make_member(name, student_id, created_at="2024-01-01"):
    return SimpleNamespace(
        id=uuid4(), name=name,
        student_id=student_id, status="active",
        created_at=created_at,
    )


def _make_participant(member_id, activity_id):
    return SimpleNamespace(id=uuid4(), member_id=member_id, activity_report_id=activity_id)


def _make_record(member_id, period="act-abc", payment_type="activity_fee"):
    return SimpleNamespace(id=uuid4(), member_id=member_id, period=period, payment_type=payment_type)


class TestDedupeLogic:
    def test_single_member_unchanged(self):
        m = _make_member("이주현", "2022130026")
        members, _, _ = _simulate_dedupe([m], [], [])
        assert len(members) == 1
        assert members[0].student_id == "2022130026"
        assert members[0].status == "active"

    def test_duplicate_becomes_inactive_null_student_id(self):
        m1 = _make_member("이주현", "2022130026", "2024-01-01")
        m2 = _make_member("이주현", "2022130026", "2024-06-01")  # newer = dup
        members, _, _ = _simulate_dedupe([m1, m2], [], [])

        active = [m for m in members if m.status == "active"]
        inactive = [m for m in members if m.status == "inactive"]

        assert len(active) == 1
        assert len(inactive) == 1
        assert active[0].student_id == "2022130026"
        # CRITICAL: duplicate's student_id must be None
        assert inactive[0].student_id is None

    def test_participants_moved_to_primary(self):
        m1 = _make_member("이주현", "2022130026", "2024-01-01")  # primary
        m2 = _make_member("이주현", "2022130026", "2024-06-01")  # dup

        act1 = uuid4()
        act2 = uuid4()
        p1 = _make_participant(m1.id, act1)  # already on primary
        p2 = _make_participant(m2.id, act2)  # dup has different activity

        _, new_participants, _ = _simulate_dedupe(
            [m1, m2], [p1, p2], []
        )

        # All participants should point to primary
        for p in new_participants:
            assert p.member_id == m1.id

    def test_participant_conflict_dropped(self):
        m1 = _make_member("이주현", "2022130026", "2024-01-01")
        m2 = _make_member("이주현", "2022130026", "2024-06-01")

        act1 = uuid4()
        # Both members already have a participant for the same activity
        p_primary = _make_participant(m1.id, act1)
        p_dup = _make_participant(m2.id, act1)  # conflict → should be dropped

        _, new_participants, _ = _simulate_dedupe(
            [m1, m2], [p_primary, p_dup], []
        )

        # Only one participant per activity after dedupe
        acts = [p.activity_report_id for p in new_participants if p.activity_report_id == act1]
        assert len(acts) == 1

    def test_unique_student_id_after_dedupe(self):
        """After dedupe, no two members should share a student_id."""
        m1 = _make_member("박민서", "2026400051", "2024-01-01")
        m2 = _make_member("박민서", "2026400051", "2024-06-01")
        m3 = _make_member("김가은", "2023100001", "2024-01-01")

        members, _, _ = _simulate_dedupe([m1, m2, m3], [], [])

        non_null_sids = [m.student_id for m in members if m.student_id is not None]
        assert len(non_null_sids) == len(set(non_null_sids)), "Duplicate student_ids remain!"
