"""Task 30 Tests: AI intent routing for activity fee transaction matching."""
from __future__ import annotations

import pytest

from app.agents.intent_router import route


class TestActivityFeeTransactionMatchIntent:
    def test_activity_fee_transaction_match_intent(self):
        result = route("활동비 매칭해줘", [])
        assert result.intent == "activity_fee_transaction_match"

    def test_activity_fee_match_keywords(self):
        for msg in [
            "이 거래내역으로 활동비 매칭해줘",
            "현재 활동 활동비 매칭해줘",
            "참가자들 활동비 입금 확인해줘",
            "활동비 입금 확인해줘",
        ]:
            result = route(msg, [])
            assert result.intent == "activity_fee_transaction_match", (
                f"'{msg}'가 {result.intent}로 잘못 라우팅되었습니다"
            )

    def test_activity_fee_match_not_payment_matching(self):
        result = route("활동비 매칭해줘", [])
        assert result.intent != "payment_matching", (
            "활동비 매칭 요청이 payment_matching으로 가면 안 됩니다"
        )

    def test_activity_fee_match_not_activity_fee_generate(self):
        result = route("활동비 매칭해줘", [])
        assert result.intent != "activity_fee_generate"


class TestClarificationWhenNoActivityId:
    def test_orchestrator_returns_clarification_without_activity_id(self, db) -> None:
        """전역 AI에서 activity_id 없이 활동비 매칭 요청 시 clarification."""
        from app.agents.assistant_orchestrator import AssistantInput, AssistantOrchestrator

        inp = AssistantInput(
            message="활동비 매칭해줘",
            activity_id=None,
            activity_mode="auto",
            requested_intent="activity_fee_transaction_match",
        )

        orchestrator = AssistantOrchestrator(db)
        response = orchestrator.run(inp)

        # Should NOT be an error or actual matching result
        # Should be clarification (general_message or asking for activity)
        assert response.intent == "activity_fee_transaction_match"
        assert "어떤 활동" in response.message or "활동 상세" in response.message, (
            f"Clarification message expected, got: {response.message}"
        )
