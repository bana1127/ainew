"""Unit tests for payment_matching_service pure-function helpers."""
import sys
import os
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

# ---------------------------------------------------------------------------
# Stub out heavy DB/ORM imports so the service module can be imported without
# a live database connection or psycopg driver.
# ---------------------------------------------------------------------------

def _make_stub_module(name: str) -> ModuleType:
    mod = ModuleType(name)
    mod.__spec__ = None  # type: ignore[attr-defined]
    return mod


# Stub psycopg / psycopg2 before anything else
for _mod_name in ("psycopg", "psycopg2", "psycopg2.extras"):
    if _mod_name not in sys.modules:
        sys.modules[_mod_name] = _make_stub_module(_mod_name)

# Stub app.core.database so create_engine is never called
_db_mod = _make_stub_module("app.core.database")
_db_mod.Base = MagicMock()  # type: ignore[attr-defined]
_db_mod.engine = MagicMock()  # type: ignore[attr-defined]
_db_mod.SessionLocal = MagicMock()  # type: ignore[attr-defined]
sys.modules["app.core.database"] = _db_mod

# Stub app.core.config so settings.DATABASE_URL is never evaluated
_cfg_mod = _make_stub_module("app.core.config")
_cfg_mod.settings = MagicMock()  # type: ignore[attr-defined]
sys.modules["app.core.config"] = _cfg_mod

# Stub the ORM models that payment_matching_service imports
_models_mod = _make_stub_module("app.models")
_models_mod.BankTransaction = MagicMock()  # type: ignore[attr-defined]
_models_mod.Member = MagicMock()  # type: ignore[attr-defined]
_models_mod.PaymentRecord = MagicMock()  # type: ignore[attr-defined]
sys.modules["app.models"] = _models_mod

_setting_mod = _make_stub_module("app.models.setting")
_setting_mod.AppSetting = MagicMock()  # type: ignore[attr-defined]
sys.modules["app.models.setting"] = _setting_mod

# Stub sqlalchemy at the session level (service top-level imports select / Session)
_sa_mod = _make_stub_module("sqlalchemy")
_sa_mod.select = MagicMock()  # type: ignore[attr-defined]
_sa_mod.and_ = MagicMock()  # type: ignore[attr-defined]
sys.modules.setdefault("sqlalchemy", _sa_mod)

_sa_orm_mod = _make_stub_module("sqlalchemy.orm")
_sa_orm_mod.Session = MagicMock()  # type: ignore[attr-defined]
sys.modules.setdefault("sqlalchemy.orm", _sa_orm_mod)

# Now it is safe to import the service
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.payment_matching_service import (  # noqa: E402
    normalize_memo,
    extract_name_candidates,
    is_excluded_transaction,
    calculate_match_score,
    match_member_from_memo,
)


# ---------------------------------------------------------------------------
# Helper: build a lightweight mock Member (no DB needed)
# ---------------------------------------------------------------------------

def make_member(name: str, student_id: str | None = None):
    return SimpleNamespace(id=uuid4(), name=name, student_id=student_id)


# ---------------------------------------------------------------------------
# is_excluded_transaction
# ---------------------------------------------------------------------------

class TestIsExcludedTransaction:
    def test_is_excluded_interest(self):
        excluded, ptype = is_excluded_transaction("예금이자", None)
        assert excluded is True
        assert ptype == "interest"

    def test_is_excluded_refund(self):
        excluded, ptype = is_excluded_transaction("환불", None)
        assert excluded is True
        assert ptype == "refund"

    def test_is_excluded_cancel(self):
        excluded, ptype = is_excluded_transaction("결제취소", None)
        assert excluded is True
        assert ptype == "refund"

    def test_not_excluded_normal(self):
        excluded, ptype = is_excluded_transaction("김가온 회비", None)
        assert excluded is False
        assert ptype == ""

    def test_not_excluded_none_memo(self):
        excluded, ptype = is_excluded_transaction(None, None)
        assert excluded is False
        assert ptype == ""

    def test_excluded_cashback(self):
        excluded, ptype = is_excluded_transaction("캐시백 지급", None)
        assert excluded is True
        assert ptype == "other"

    def test_excluded_keyword_embedded(self):
        # keyword appears inside a longer memo string
        excluded, ptype = is_excluded_transaction("이번달 예금이자 입금", None)
        assert excluded is True
        assert ptype == "interest"


# ---------------------------------------------------------------------------
# normalize_memo
# ---------------------------------------------------------------------------

class TestNormalizeMemo:
    def test_normalize_memo_strips_prefix(self):
        result = normalize_memo("토스 김가온")
        assert result == "김가온"

    def test_normalize_memo_strips_suffix(self):
        result = normalize_memo("김가온 회비")
        assert result == "김가온"

    def test_normalize_memo_strips_multiple_prefixes(self):
        # "메모아" is also a recognized prefix
        result = normalize_memo("메모아 이예은")
        assert result == "이예은"

    def test_normalize_memo_strips_kakaopay_prefix(self):
        result = normalize_memo("카카오페이 홍길동")
        assert result == "홍길동"

    def test_normalize_memo_no_change_plain_name(self):
        result = normalize_memo("홍길동")
        assert result == "홍길동"

    def test_normalize_memo_collapses_spaces(self):
        result = normalize_memo("  토스   김가온  ")
        assert result == "김가온"

    def test_normalize_memo_strips_trailing_납부(self):
        result = normalize_memo("김가온 납부")
        assert result == "김가온"


# ---------------------------------------------------------------------------
# extract_name_candidates
# ---------------------------------------------------------------------------

class TestExtractNameCandidates:
    def test_extract_name_candidates_basic(self):
        candidates = extract_name_candidates("토스 김가온")
        assert "김가온" in candidates

    def test_extract_candidates_includes_substrings(self):
        # "이예은" -> substrings of length 2: "이예", "예은"; length 3: "이예은"
        candidates = extract_name_candidates("이예은")
        assert "이예은" in candidates
        assert "이예" in candidates
        assert "예은" in candidates

    def test_extract_candidates_empty_memo(self):
        candidates = extract_name_candidates("")
        assert candidates == []

    def test_extract_candidates_no_korean(self):
        candidates = extract_name_candidates("abc123")
        assert candidates == []


# ---------------------------------------------------------------------------
# calculate_match_score
# ---------------------------------------------------------------------------

class TestCalculateMatchScore:
    def test_exact_match_score_is_1(self):
        score = calculate_match_score("홍길동", "홍길동")
        assert score == 1.0

    def test_substring_gives_at_least_0_9(self):
        # candidate is a substring of member_name
        score = calculate_match_score("길동", "홍길동")
        assert score >= 0.9

    def test_completely_different_is_low(self):
        score = calculate_match_score("가나다", "홍길동")
        assert score < 0.5

    def test_member_name_substring_of_candidate(self):
        # member_name is substring of candidate
        score = calculate_match_score("홍길동이다", "홍길동")
        assert score >= 0.9


# ---------------------------------------------------------------------------
# match_member_from_memo
# ---------------------------------------------------------------------------

class TestMatchMemberFromMemo:
    def test_exact_name_match(self):
        members = [make_member("김가온")]
        member, score, status, reason = match_member_from_memo(
            "토스 김가온", {}, members, threshold=0.8
        )
        assert member is not None
        assert member.name == "김가온"
        assert score >= 0.9
        assert status == "matched"

    def test_normalized_match_no_space(self):
        # "메모아이예은" normalizes to "이예은" after stripping "메모아" prefix
        members = [make_member("이예은")]
        member, score, status, reason = match_member_from_memo(
            "메모아이예은", {}, members, threshold=0.8
        )
        assert member is not None
        assert member.name == "이예은"
        assert status == "matched"

    def test_similarity_match(self):
        members = [make_member("홍길동")]
        member, score, status, reason = match_member_from_memo(
            "홍길동", {}, members, threshold=0.8
        )
        assert member is not None
        assert member.name == "홍길동"
        assert score == 1.0
        assert status == "matched"

    def test_unmatched(self):
        members = [make_member("김가온"), make_member("이예은")]
        member, score, status, reason = match_member_from_memo(
            "이체수수료", {}, members, threshold=0.8
        )
        assert status == "unmatched"

    def test_multiple_candidates_need_check(self):
        # Use members whose names are similar enough to a shared candidate
        # "길동" is a 2-char substring of both "홍길동" and "이길동" → both score >= threshold
        members = [make_member("홍길동"), make_member("이길동")]
        member, score, status, reason = match_member_from_memo(
            "길동", {}, members, threshold=0.6
        )
        assert status == "need_check"

    def test_student_id_match(self):
        m = make_member("김가온", student_id="20230001")
        student_id_map = {"20230001": m}
        member, score, status, reason = match_member_from_memo(
            "20230001 입금", student_id_map, [m], threshold=0.8
        )
        assert member is not None
        assert member.name == "김가온"
        assert score == 1.0
        assert status == "matched"

    def test_empty_memo_unmatched(self):
        members = [make_member("김가온")]
        member, score, status, reason = match_member_from_memo(
            "", {}, members, threshold=0.8
        )
        assert member is None
        assert status == "unmatched"

    def test_none_memo_unmatched(self):
        members = [make_member("김가온")]
        member, score, status, reason = match_member_from_memo(
            None, {}, members, threshold=0.8
        )
        assert member is None
        assert status == "unmatched"
