"""Task 28/33 Tests: Intent routing matrix — ensures correct classification."""
from __future__ import annotations

import pytest

from app.agents.intent_router import route


class TestMembershipFeeGenerate:
    """Task 33: '이번 학기 회비 대상 생성해줘' → membership_fee_generate."""

    def test_이번_학기_회비_대상_생성(self):
        result = route("이번 학기 회비 대상 생성해줘", [])
        assert result.intent == "membership_fee_generate", (
            f"Expected membership_fee_generate, got {result.intent}"
        )

    def test_회비_납부_대상_생성(self):
        result = route("회비 납부 대상 생성해줘", [])
        assert result.intent == "membership_fee_generate"

    def test_never_routes_to_activity_fee(self):
        result = route("이번 학기 회비 대상 생성해줘", [])
        assert result.intent != "activity_fee_generate", (
            "회비 대상 생성이 activity_fee_generate로 잘못 라우팅되었습니다"
        )


class TestActivityFeeTransactionMatchRouting:
    """Task 33: Activity fee transaction match commands → activity_fee_transaction_match."""

    def test_활동비_매칭해줘(self):
        result = route("활동비 매칭해줘", [])
        assert result.intent == "activity_fee_transaction_match"

    def test_활동비_입금_확인해줘(self):
        result = route("참가자들 활동비 입금 확인해줘", [])
        assert result.intent == "activity_fee_transaction_match"

    def test_이_거래내역으로_활동비_매칭(self):
        result = route("이 거래내역으로 활동비 매칭해줘", [])
        assert result.intent == "activity_fee_transaction_match"

    def test_활동비_납부_확인(self):
        result = route("활동비 납부 확인해줘", [])
        assert result.intent == "activity_fee_transaction_match"

    def test_never_routes_to_membership_matching(self):
        """활동비 매칭이 payment_matching(회비)으로 가면 안 됨."""
        result = route("활동비 매칭해줘", [])
        assert result.intent != "payment_matching", (
            "활동비 매칭 요청이 payment_matching(회비)으로 잘못 라우팅되었습니다"
        )


class TestBulkMembershipFeeMarkPaid:
    def test_전체_회비_완납_처리(self):
        result = route("전체 회비 완납 처리해줘", [])
        assert result.intent == "bulk_membership_fee_mark_paid", (
            f"Expected bulk_membership_fee_mark_paid, got {result.intent}"
        )

    def test_현재_멤버_전부_각각_회비에_맞춰서_완납(self):
        result = route("현재 멤버 전부 각각 회비에 맞춰서 완납 처리해줘", [])
        assert result.intent == "bulk_membership_fee_mark_paid", (
            f"Expected bulk_membership_fee_mark_paid, got {result.intent}"
        )

    def test_이번_학기_회비_전부_납부_완료로(self):
        result = route("이번 학기 회비 전부 납부 완료로 바꿔줘", [])
        assert result.intent == "bulk_membership_fee_mark_paid"

    def test_부원들_회비_다_냈다고(self):
        result = route("부원들 회비 다 냈다고 처리해줘", [])
        assert result.intent == "bulk_membership_fee_mark_paid"

    def test_회비_일괄_완납(self):
        result = route("회비 일괄 완납 처리", [])
        assert result.intent == "bulk_membership_fee_mark_paid"

    def test_never_routes_to_payment_matching(self):
        """전체 회비 완납은 절대 payment_matching으로 가면 안 됨."""
        result = route("전체 회비 완납 처리해줘", [])
        assert result.intent != "payment_matching", (
            "bulk 요청이 payment_matching으로 잘못 라우팅되었습니다"
        )

    def test_멤버들_전부_회비(self):
        result = route("멤버들 전부 회비 완납 처리해줘", [])
        assert result.intent == "bulk_membership_fee_mark_paid"


class TestPaymentMatchingRouting:
    def test_거래내역_회비_매칭(self):
        result = route("거래내역에서 회비 납부 확인해줘", [])
        assert result.intent == "payment_matching"

    def test_통장내역_회비_매칭(self):
        result = route("통장내역 회비랑 매칭해줘", [])
        assert result.intent == "payment_matching"

    def test_이_거래내역으로_회비_매칭(self):
        result = route("이 거래내역으로 회비 매칭해줘", [])
        assert result.intent == "payment_matching"


class TestActivityFeeRouting:
    def test_활동비_생성(self):
        result = route("활동비 생성해줘", [])
        assert result.intent == "activity_fee_generate"

    def test_참가비_설정(self):
        result = route("참가비 설정해줘", [])
        assert result.intent == "activity_fee_generate"


class TestManualPaymentUpdate:
    def test_박민서_냈어(self):
        result = route("박민서가 냈어", [])
        assert result.intent == "payment_manual_update"

    def test_김철수_학생_납부완료(self):
        result = route("김철수 학생 납부완료로 바꿔줘", [])
        assert result.intent == "payment_manual_update"
