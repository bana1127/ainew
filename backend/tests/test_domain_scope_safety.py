# -*- coding: utf-8 -*-
"""Task 33: Domain scope safety tests.

Verifies that intent routing keeps membership_fee and activity_fee strictly
separated, and that activity-scoped commands require an activity_id.

These tests work without a live DB because they only exercise the rule-based
intent router.
"""
from __future__ import annotations

import pytest

from app.agents.intent_router import route


# ── 1. Membership fee commands never touch activity_fee ───────────────────────

class TestMembershipFeeDoesNotTouchActivityFee:
    """All 회비 (membership_fee) commands must not route to activity_fee intents."""

    MEMBERSHIP_FEE_COMMANDS = [
        "전체 회비 완납 처리해줘",
        "현재 멤버 전부 각각 회비에 맞춰서 완납 처리해줘",
        "거래내역에서 회비 납부 확인해줘",
        "이번 학기 회비 대상 생성해줘",
        "회비 납부 대상 생성해줘",
        "미납자 확인해줘",
        "회비 일괄 완납 처리",
    ]

    ACTIVITY_FEE_INTENTS = {
        "activity_fee_generate",
        "activity_fee_transaction_match",
    }

    def test_membership_commands_not_activity_fee(self):
        for cmd in self.MEMBERSHIP_FEE_COMMANDS:
            result = route(cmd, [])
            assert result.intent not in self.ACTIVITY_FEE_INTENTS, (
                f"회비 명령 '{cmd}'이 activity_fee intent '{result.intent}'로 잘못 라우팅되었습니다"
            )


# ── 2. Activity fee commands never touch membership_fee ───────────────────────

class TestActivityFeeDoesNotTouchMembershipFee:
    """All 활동비 (activity_fee) commands must not route to membership_fee intents."""

    ACTIVITY_FEE_COMMANDS = [
        "활동비 매칭해줘",
        "이 거래내역으로 활동비 매칭해줘",
        "참가자들 활동비 입금 확인해줘",
        "활동비 납부 확인해줘",
        "활동비 10000원 납부 대상 만들어줘",
        "참가비 설정해줘",
    ]

    MEMBERSHIP_FEE_INTENTS = {
        "bulk_membership_fee_mark_paid",
        "membership_fee_generate",
        "payment_matching",
    }

    def test_activity_commands_not_membership_fee(self):
        for cmd in self.ACTIVITY_FEE_COMMANDS:
            result = route(cmd, [])
            assert result.intent not in self.MEMBERSHIP_FEE_INTENTS, (
                f"활동비 명령 '{cmd}'이 membership_fee intent '{result.intent}'로 잘못 라우팅되었습니다"
            )


# ── 3. Activity-scoped intents require activity context ───────────────────────

class TestActivityScopedIntentsNeedActivityId:
    """Commands that are activity-scoped should route to activity_fee_* intents.

    The orchestrator will check for activity_id and return clarification if missing.
    We verify the intent routing is correct so the orchestrator can enforce the scope.
    """

    def test_활동비_매칭_routes_to_activity_fee_match(self):
        """Global '활동비 매칭해줘' routes to activity_fee_transaction_match.
        The orchestrator will ask '어떤 활동?' if no activity_id is linked.
        """
        result = route("활동비 매칭해줘", [])
        assert result.intent == "activity_fee_transaction_match"

    def test_활동비_생성_routes_to_activity_fee_generate(self):
        result = route("활동비 10000원 납부 대상 만들어줘", [])
        assert result.intent == "activity_fee_generate"

    def test_박민서_활동비_납부_routes_to_manual_update(self):
        result = route("박민서 활동비 25000원 냈어", [])
        assert result.intent == "payment_manual_update"


# ── 4. Bulk mark paid never uses fixed amount or activity_fee ─────────────────

class TestBulkMarkPaidScope:
    """bulk_membership_fee_mark_paid must be exclusively membership_fee domain."""

    def test_전체_회비_is_bulk_not_activity(self):
        result = route("전체 회비 완납 처리해줘", [])
        assert result.intent == "bulk_membership_fee_mark_paid"
        # Must NOT be activity_fee_generate
        assert result.intent != "activity_fee_generate"
        assert result.intent != "activity_fee_transaction_match"

    def test_멤버_회비_각각_is_bulk(self):
        result = route("현재 멤버 전부 각각 회비에 맞춰서 완납 처리해줘", [])
        assert result.intent == "bulk_membership_fee_mark_paid"


# ── 5. Payment matching exclusively for membership_fee ───────────────────────

class TestPaymentMatchingMembershipOnly:
    """payment_matching should be used for membership_fee transactions, not activity_fee."""

    def test_거래내역_회비_납부_확인(self):
        result = route("거래내역에서 회비 납부 확인해줘", [])
        assert result.intent == "payment_matching"

    def test_미납자_확인(self):
        result = route("미납자 확인해줘", [])
        # Should route to payment_matching or bulk, not activity_fee
        assert result.intent not in {"activity_fee_generate", "activity_fee_transaction_match"}, (
            f"'미납자 확인해줘'가 activity_fee intent '{result.intent}'로 잘못 라우팅되었습니다"
        )

    def test_통장내역_회비_매칭(self):
        result = route("통장내역 회비랑 매칭해줘", [])
        assert result.intent == "payment_matching"


# ── 6. Activity fee transaction match clarification ──────────────────────────

class TestActivityFeeTransactionMatchClarification:
    """When activity_fee_transaction_match is triggered globally (no activity linked),
    the orchestrator returns a clarification. We verify the routing is correct so
    the orchestrator can handle it.
    """

    def test_활동비_매칭해줘_without_activity(self):
        """Routes to activity_fee_transaction_match so orchestrator can return clarification."""
        result = route("활동비 매칭해줘", [])
        assert result.intent == "activity_fee_transaction_match", (
            "활동비 매칭해줘 must route to activity_fee_transaction_match; "
            "the orchestrator enforces activity_id requirement"
        )

    def test_활동비_완납_without_activity(self):
        """'활동비 완납 처리해줘' routes to activity_fee_generate.
        The orchestrator will ask 'which activity?' if no activity_id is linked.
        """
        result = route("활동비 완납 처리해줘", [])
        assert result.intent == "activity_fee_generate", (
            "활동비 완납 처리해줘 must route to activity_fee_generate; "
            "orchestrator returns '어떤 활동의 활동비를 처리할까요?' if no activity linked"
        )
