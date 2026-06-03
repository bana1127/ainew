# -*- coding: utf-8 -*-
"""Tests for Task 23 manual payment update hotfix.

Covers:
  - Intent routing: '박민서가 25000원 냈어' → payment_manual_update
  - Intent routing: '제출했어', '보냈어', '송금했어' variants also route correctly
  - Intent routing: '활동비 25000원으로 바꿔줘' (no name) → NOT payment_manual_update
  - Name extraction: suffix stripping, noise filtering
  - Amount parsing: 한글 수 표현 (이만원, 이만오천원, 만오천원, etc.)
  - Status recalculation: unpaid/partial/paid/overpaid
  - No change to required_amount for other participants (documented scenario)
"""
from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import MagicMock

import pytest


# ---------------------------------------------------------------------------
# Stubs — keep identical to other test files in this project
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

# SQLAlchemy stubs
_sa = _stub("sqlalchemy")
for _attr in ("select", "and_", "or_", "func", "update", "Index", "String", "Text",
              "Boolean", "DateTime", "Date", "Integer", "BigInteger",
              "UniqueConstraint", "ForeignKey"):
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

for _mod_name3 in ("app.agents.activity_resolver", "app.schemas.assistant"):
    if _mod_name3 not in sys.modules:
        _m4 = _stub(_mod_name3)
        _m4.resolve_activity_context = MagicMock()  # type: ignore[attr-defined]
        _m4.ActivityResolutionResult = MagicMock  # type: ignore[attr-defined]
        _m4.AssistantExecuteResponse = MagicMock  # type: ignore[attr-defined]
        sys.modules[_mod_name3] = _m4

# Only import pure functions
from app.agents.intent_router import route  # noqa: E402
from app.services.payment_manual_update_service import (  # noqa: E402
    extract_member_name,
    parse_payment_amount,
    _recalculate_status,
)


# ============================================================
# Part A: Intent routing — payment_manual_update priority
# ============================================================

class TestPaymentManualUpdateRouting:
    """Verify messages with name + payment verb → payment_manual_update."""

    def test_제출했어_with_활동비(self):
        """'박민서 학생이 활동비 25000원 제출했어' must NOT go to activity_fee_generate."""
        result = route(
            message="박민서 학생이 활동비 25000원 제출했어",
            file_names=[],
        )
        assert result.intent == "payment_manual_update", (
            f"Expected payment_manual_update, got {result.intent}. "
            "'제출했어' must be in PAYMENT_MARK_KEYWORDS and take priority over "
            "activity_fee_generate."
        )

    def test_냈어_basic(self):
        """'박민서가 25000원 냈어' → payment_manual_update."""
        result = route(message="박민서가 25000원 냈어", file_names=[])
        assert result.intent == "payment_manual_update"

    def test_납부_완료로_바꿔(self):
        """'박민서 납부 완료로 바꿔줘' → payment_manual_update."""
        result = route(message="박민서 납부 완료로 바꿔줘", file_names=[])
        assert result.intent == "payment_manual_update"

    def test_보냈어(self):
        result = route(message="박민서가 2만원 보냈어", file_names=[])
        assert result.intent == "payment_manual_update"

    def test_송금했어(self):
        result = route(message="이도윤 25000원 송금했어", file_names=[])
        assert result.intent == "payment_manual_update"

    def test_납부했어_기본(self):
        result = route(message="박민서 학생이 활동비 15000원을 납부했어", file_names=[])
        assert result.intent == "payment_manual_update"

    def test_입금했어(self):
        result = route(message="김가은님 2만5천원 입금했어", file_names=[])
        assert result.intent == "payment_manual_update"

    def test_납부_완료_standalone(self):
        """'납부 완료' alone (no verb suffix) should also trigger payment_manual_update."""
        result = route(message="이도윤 납부 완료", file_names=[])
        assert result.intent == "payment_manual_update"


class TestActivityFeeUpdateNotManual:
    """Messages without name + payment verb → NOT payment_manual_update."""

    def test_활동비_금액_변경_no_name(self):
        """'활동비 25000원으로 바꿔줘' has no person name → activity_fee_generate."""
        result = route(message="활동비 25000원으로 바꿔줘", file_names=[])
        assert result.intent != "payment_manual_update", (
            f"Got payment_manual_update but expected activity_fee_generate. "
            "A message with no person name should NOT route to payment_manual_update."
        )
        assert result.intent == "activity_fee_generate"

    def test_금액만_있을_때(self):
        """'25000원으로 맞춰줘' (no name, no payment verb) → not payment_manual_update."""
        result = route(message="25000원으로 맞춰줘", file_names=[])
        assert result.intent != "payment_manual_update"

    def test_이름없는_납부완료는_manual_아님(self):
        """A payment verb without a person name must not update an arbitrary member."""
        result = route(message="활동비 납부 완료로 바꿔줘", file_names=[])
        assert result.intent != "payment_manual_update"

    def test_활동비_생성_키워드(self):
        result = route(message="참여자 기준으로 활동비 10000원 납부 대상 만들어줘", file_names=[])
        assert result.intent == "activity_fee_generate"


# ============================================================
# Part B: Name extraction
# ============================================================

class TestExtractMemberName:
    def test_suffix_haksaeng(self):
        assert extract_member_name("박민서 학생이 활동비 25000원 제출했어") == "박민서"

    def test_suffix_nim(self):
        assert extract_member_name("김가은님 2만원 냈어") == "김가은"

    def test_no_suffix(self):
        assert extract_member_name("이도윤 납부 완료로 바꿔줘") == "이도윤"

    def test_noise_not_returned(self):
        """'활동비 납부 완료로 바꿔줘' — no person name."""
        result = extract_member_name("활동비 납부 완료로 바꿔줘")
        assert result not in ("활동비", "납부", "완료", "바꿔", "처리"), (
            f"Extracted '{result}' which is a noise word, not a person name."
        )

    def test_suffix_씨(self):
        assert extract_member_name("박민서씨 3만원 송금했어") == "박민서"

    def test_suffix_부원(self):
        assert extract_member_name("이지우 부원이 제출했어") == "이지우"


# ============================================================
# Part C: Amount parsing
# ============================================================

class TestParsePaymentAmount:
    # Digit-based
    def test_plain_25000(self):
        assert parse_payment_amount("박민서 25000원 냈어") == 25000

    def test_comma_25000(self):
        assert parse_payment_amount("25,000원 납부했어") == 25000

    def test_2man_won(self):
        assert parse_payment_amount("2만원 냈어") == 20000

    def test_1man_5cheon(self):
        assert parse_payment_amount("1만5천원 입금") == 15000

    def test_2man_5cheon_digit(self):
        assert parse_payment_amount("2만5천원 제출했어") == 25000

    # Korean-char-based
    def test_이만원(self):
        assert parse_payment_amount("이만원 냈어") == 20000

    def test_이만오천원(self):
        assert parse_payment_amount("이만오천원 제출했어") == 25000

    def test_삼만원(self):
        assert parse_payment_amount("삼만원 보냈어") == 30000

    def test_만오천원(self):
        assert parse_payment_amount("만오천원 납부") == 15000

    def test_만원(self):
        assert parse_payment_amount("만원 냈어") == 10000

    # No amount
    def test_no_amount_납부_완료(self):
        assert parse_payment_amount("납부 완료로 바꿔줘") is None

    def test_no_amount_name_only(self):
        assert parse_payment_amount("박민서 납부 처리해줘") is None


# ============================================================
# Part E: Status recalculation
# ============================================================

class TestRecalculateStatus:
    def test_full_pay_paid(self):
        assert _recalculate_status(25000, 25000, "unpaid") == "paid"

    def test_partial(self):
        assert _recalculate_status(20000, 25000, "unpaid") == "partial"

    def test_overpaid(self):
        assert _recalculate_status(30000, 25000, "unpaid") == "overpaid"

    def test_zero_unpaid(self):
        assert _recalculate_status(0, 25000, "unpaid") == "unpaid"

    def test_exempt_preserved(self):
        assert _recalculate_status(0, 25000, "exempt") == "exempt"

    def test_partial_to_paid(self):
        assert _recalculate_status(25000, 25000, "partial") == "paid"


# ============================================================
# Part F: Scenario documentation (integration — no live DB)
# ============================================================

class TestScenarioDocumentation:
    """Documents the expected end-to-end behavior.

    These tests verify the routing + parsing portions only.
    DB interaction is verified in E2E / integration tests.

    Scenario: Activity with 19 participants, required_amount=25,000
    박민서 status=unpaid initially.

    1. '박민서 학생이 활동비 25000원 제출했어'
       → intent=payment_manual_update, name=박민서, amount=25000
       → paid_amount=25000, status=paid
       → other 18 participants unchanged
       → required_amount stays 25,000

    2. '박민서가 2만원 냈어'
       → intent=payment_manual_update, name=박민서, amount=20000
       → paid_amount=20000, status=partial

    3. '박민서 납부 완료로 바꿔줘' (no amount)
       → intent=payment_manual_update, name=박민서, amount=None
       → paid_amount=required_amount=25000, status=paid

    4. '박민서 3만원 냈어'
       → intent=payment_manual_update, name=박민서, amount=30000
       → paid_amount=30000, status=overpaid

    5. '활동비 25000원으로 바꿔줘'
       → intent=activity_fee_generate (NOT payment_manual_update)
       → no individual record update

    6. '박민서 25000원 냈어'
       → intent=payment_manual_update
       → only 박민서 record changes (required_amount unchanged for all)
    """

    def test_scenario1_routing(self):
        result = route(message="박민서 학생이 활동비 25000원 제출했어", file_names=[])
        assert result.intent == "payment_manual_update"

    def test_scenario1_parsing(self):
        assert extract_member_name("박민서 학생이 활동비 25000원 제출했어") == "박민서"
        assert parse_payment_amount("박민서 학생이 활동비 25000원 제출했어") == 25000
        assert _recalculate_status(25000, 25000, "unpaid") == "paid"

    def test_scenario2_parsing(self):
        assert extract_member_name("박민서가 2만원 냈어") == "박민서"
        assert parse_payment_amount("박민서가 2만원 냈어") == 20000
        assert _recalculate_status(20000, 25000, "unpaid") == "partial"

    def test_scenario3_no_amount(self):
        """No amount given → paid_amount = required_amount → status=paid."""
        assert extract_member_name("박민서 납부 완료로 바꿔줘") == "박민서"
        assert parse_payment_amount("박민서 납부 완료로 바꿔줘") is None
        # When amount is None, service sets paid = required (25000)
        assert _recalculate_status(25000, 25000, "unpaid") == "paid"

    def test_scenario4_overpaid(self):
        assert parse_payment_amount("박민서 3만원 냈어") == 30000
        assert _recalculate_status(30000, 25000, "unpaid") == "overpaid"

    def test_scenario5_no_name_not_manual(self):
        """'활동비 25000원으로 바꿔줘' → NOT payment_manual_update."""
        result = route(message="활동비 25000원으로 바꿔줘", file_names=[])
        assert result.intent != "payment_manual_update"

    def test_scenario6_routing(self):
        """'박민서 25000원 냈어' → payment_manual_update (not fee_generate)."""
        result = route(message="박민서 25000원 냈어", file_names=[])
        assert result.intent == "payment_manual_update"
