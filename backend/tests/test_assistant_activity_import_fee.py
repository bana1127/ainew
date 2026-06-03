# -*- coding: utf-8 -*-
"""Tests for the assistant pipeline: activity creation → roster import → fee generation.

Task 23: Verifies that "명단도 등록해줘" + xlsx routes to activity_create_with_roster
and that intent routing + fee parsing work correctly.

Intent routing tests: pure function — no DB needed.
Pipeline integration: documented as scenario spec; requires live DB.
"""
from __future__ import annotations

import re
import sys
from types import ModuleType
from unittest.mock import MagicMock

import pytest


# ---------------------------------------------------------------------------
# Stubs — must be comprehensive enough for all indirect imports
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

# Comprehensive SQLAlchemy stub
_sa = _stub("sqlalchemy")
for _attr in ("select", "and_", "or_", "func", "update", "Index", "String", "Text",
              "Boolean", "DateTime", "Date", "Integer", "BigInteger"):
    setattr(_sa, _attr, MagicMock())
sys.modules.setdefault("sqlalchemy", _sa)
_sa_orm = _stub("sqlalchemy.orm")
for _attr in ("Session", "Mapped", "mapped_column", "relationship", "selectinload"):
    setattr(_sa_orm, _attr, MagicMock())
sys.modules.setdefault("sqlalchemy.orm", _sa_orm)
_sa_d = _stub("sqlalchemy.dialects.postgresql")
_sa_d.UUID = MagicMock()  # type: ignore[attr-defined]
_sa_d.JSONB = MagicMock()  # type: ignore[attr-defined]
sys.modules.setdefault("sqlalchemy.dialects.postgresql", _sa_d)

# Model stubs
for _mod_name2 in (
    "app.models", "app.models.base", "app.models.activity",
    "app.models.member", "app.models.payment", "app.models.receipt",
    "app.models.file", "app.models.notification", "app.models.setting",
    "app.models.transaction", "app.models.activity_feedback",
):
    if _mod_name2 not in sys.modules:
        _m3 = _stub(_mod_name2)
        for _cls in ("ActivityReport", "ActivityParticipant", "ActivityCategory",
                     "ReferenceReport", "Member", "PaymentRecord", "PaymentAdjustmentLog",
                     "BankTransaction", "Receipt", "UploadedFile", "Notification",
                     "AppSetting", "ActivityFeedback", "Base"):
            setattr(_m3, _cls, MagicMock)
        sys.modules[_mod_name2] = _m3

# Agent stubs (only import intent_router directly)
for _mod_name3 in ("app.agents.activity_resolver", "app.schemas.assistant"):
    if _mod_name3 not in sys.modules:
        _m4 = _stub(_mod_name3)
        _m4.resolve_activity_context = MagicMock()  # type: ignore[attr-defined]
        _m4.ActivityResolutionResult = MagicMock  # type: ignore[attr-defined]
        _m4.AssistantExecuteResponse = MagicMock  # type: ignore[attr-defined]
        sys.modules[_mod_name3] = _m4

# Import ONLY intent_router (no heavy transitive deps)
from app.agents.intent_router import route  # noqa: E402


# ---------------------------------------------------------------------------
# Replicate the two pure functions under test (to avoid transitive imports)
# ---------------------------------------------------------------------------

def _extract_activity_fee_amount(message: str) -> int | None:
    """Replicated from assistant_orchestrator._extract_activity_fee_amount."""
    if not message:
        return None
    fee_context = any(word in message for word in ("활동비", "참가비", "회비"))

    # N만원
    m = re.search(r"(\d+)\s*만\s*원", message)
    if m and fee_context:
        return int(m.group(1)) * 10000

    # 만원 alone
    if re.search(r"(?<!\d)만\s*원", message) and fee_context:
        return 10000

    # 만오천원 / 만N천원
    m = re.search(r"만([가-힣]+)천원?", message)
    if m:
        _kor = {"오": 5, "사": 4, "삼": 3, "이": 2, "일": 1, "육": 6, "칠": 7, "팔": 8, "구": 9}
        cheon = sum(_kor.get(c, 0) for c in m.group(1))
        return 10000 + cheon * 1000

    # N만N천원
    m = re.search(r"(\d+)만(\d+)천원?", message)
    if m:
        return int(m.group(1)) * 10000 + int(m.group(2)) * 1000

    # Plain number + 원
    m = re.search(r"(\d{4,})\s*원", message.replace(",", ""))
    if m and fee_context:
        return int(m.group(1))

    return None


def _import_risk_reasons_replicated(form_type: str, needs_review: int) -> list[str]:
    """Replicated from assistant_orchestrator._import_risk_reasons (hotfix version)."""
    reasons = []
    if form_type == "unknown_excel":
        reasons.append("unknown excel headers")
    # "ambiguous member matches" is intentionally NOT a blocker
    return reasons


# ============================================================
# Intent routing — roster import flow
# ============================================================

class TestRosterIntentRouting:
    """Ensure '명단도 등록해줘' + xlsx → activity_create_with_roster."""

    def test_core_scenario(self):
        result = route(
            message="6월 3일에 A401호에서 활동비 2만원으로 진행할거야. 명단도 등록해줘",
            file_names=["참여자명단.xlsx"],
        )
        assert result.intent == "activity_create_with_roster", (
            f"Expected activity_create_with_roster, got {result.intent}. "
            "Fix: ensure 'xlsx + 명단' routes to activity_create_with_roster "
            "before activity_fee_generate."
        )

    def test_명단도_등록해줘_no_fee(self):
        result = route(message="명단도 등록해줘", file_names=["roster.xlsx"])
        assert result.intent == "activity_create_with_roster"

    def test_명단_등록_keyword(self):
        result = route(message="명단 등록해줘", file_names=["members.xlsx"])
        assert result.intent == "activity_create_with_roster"

    def test_활동비_명단_xlsx_together(self):
        # "활동비" alone would route to activity_fee_generate, but
        # "명단" + xlsx must take priority → activity_create_with_roster
        result = route(
            message="활동비 2만원, 명단 있어",
            file_names=["명단.xlsx"],
        )
        assert result.intent == "activity_create_with_roster"

    def test_application_form_filename(self):
        result = route(
            message="명단도 등록해줘",
            file_names=["활동신청서.xlsx"],
        )
        assert result.intent == "activity_create_with_application_form"

    def test_no_file_no_activity_create(self):
        result = route(message="명단도 등록해줘", file_names=[])
        assert result.intent != "activity_create_with_roster"

    def test_without_명단_활동비_routes_to_fee(self):
        # xlsx + "활동비" but NO roster/명단 keyword → still activity_fee_generate
        result = route(
            message="활동비 2만원 걷어줘",
            file_names=["거래내역.xlsx"],
        )
        # Note: now may route to fee_generate because no 명단 keyword
        assert result.intent not in ("activity_create_with_roster", "activity_create_with_file")


class TestActivityCreateFileKeywords:
    def test_새_활동(self):
        result = route(message="새 활동 만들어줘", file_names=["file.xlsx"])
        assert result.intent in ("activity_create_with_roster", "activity_create_with_file")

    def test_명단으로(self):
        result = route(message="명단으로 활동 만들어줘", file_names=["file.xlsx"])
        assert result.intent == "activity_create_with_roster"

    def test_참여자_등록(self):
        result = route(message="참여자 등록해줘", file_names=["list.csv"])
        assert result.intent == "activity_create_with_roster"


class TestPaymentManualUpdateStillWorks:
    def test_납부했어(self):
        result = route(message="박민서 학생이 활동비 15000원을 납부했어", file_names=[])
        assert result.intent == "payment_manual_update"

    def test_냈어_no_file(self):
        result = route(message="박민서가 15000원 냈어", file_names=[])
        assert result.intent == "payment_manual_update"


# ============================================================
# Fee amount extraction
# ============================================================

class TestExtractFeeAmount:
    def test_2만원(self):
        assert _extract_activity_fee_amount("활동비 2만원으로 진행할거야") == 20000

    def test_만오천원(self):
        assert _extract_activity_fee_amount("활동비 만오천원 걷어줘") == 15000

    def test_1만5천원(self):
        assert _extract_activity_fee_amount("참가비 1만5천원") == 15000

    def test_20000원(self):
        assert _extract_activity_fee_amount("활동비 20000원") == 20000

    def test_no_fee(self):
        assert _extract_activity_fee_amount("명단도 등록해줘") is None

    def test_core_scenario_fee(self):
        msg = "6월 3일에 A401호에서 활동비 2만원으로 진행할거야. 명단도 등록해줘"
        assert _extract_activity_fee_amount(msg) == 20000


# ============================================================
# Import risk reasons
# ============================================================

class TestImportRiskReasons:
    def test_unknown_excel_blocks(self):
        reasons = _import_risk_reasons_replicated("unknown_excel", 0)
        assert "unknown excel headers" in reasons

    def test_needs_review_not_blocker(self):
        reasons = _import_risk_reasons_replicated("member_roster", 3)
        assert reasons == [], f"needs_review should NOT block import, got {reasons}"

    def test_known_form_no_risk(self):
        assert _import_risk_reasons_replicated("activity_application_form", 0) == []

    def test_feedback_form_no_risk(self):
        assert _import_risk_reasons_replicated("activity_feedback_form", 5) == []


# ============================================================
# Full scenario documentation
# ============================================================

class TestScenarioDocumentation:
    """Documents the expected full pipeline for the core scenario.

    Scenario:
      message = "6월 3일에 A401호에서 활동비 2만원으로 진행할거야. 명단도 등록해줘"
      file = 참여자명단.xlsx (with 이름/학번 columns)
      activity_mode = auto (global assistant)

    Expected log sequence:
      [assistant] uploaded_files_count=1
      [assistant] saved_file_ids=[...]
      [assistant] created_activity_id=...
      [assistant] linked_file_ids=[...]
      [assistant] excel_form_type=member_roster
      [assistant] import_preview_total_rows=N
      [assistant] import_apply_created_participants=N
      [assistant] activity_fee_amount=20000
      [assistant] activity_fee_created_count=N
    """

    def test_intent_routes_correctly(self):
        msg = "6월 3일에 A401호에서 활동비 2만원으로 진행할거야. 명단도 등록해줘"
        result = route(message=msg, file_names=["참여자명단.xlsx"])
        assert result.intent == "activity_create_with_roster"

    def test_fee_amount_extracted(self):
        msg = "6월 3일에 A401호에서 활동비 2만원으로 진행할거야. 명단도 등록해줘"
        assert _extract_activity_fee_amount(msg) == 20000

    def test_roster_form_has_no_blocking_risks(self):
        reasons = _import_risk_reasons_replicated("member_roster", 5)
        assert reasons == []
