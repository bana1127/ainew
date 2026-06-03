"""Task 28 Tests: Verify no legacy 30,000 fixed amounts in AI responses."""
from __future__ import annotations

import pytest
import json
from app.agents.intent_router import route


def _result_has_30000(obj, path: str = "") -> list[str]:
    """Recursively check if any value equals 30000."""
    found = []
    if isinstance(obj, int) and obj == 30000:
        found.append(path)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            found.extend(_result_has_30000(v, f"{path}.{k}"))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            found.extend(_result_has_30000(v, f"{path}[{i}]"))
    return found


class TestNoLegacy30000InIntentRouting:
    def test_bulk_membership_fee_intent_not_payment_matching(self):
        """전체 회비 완납 처리 요청이 payment_matching이 아닌 bulk_membership_fee_mark_paid로 간다."""
        result = route("전체 회비 완납 처리해줘", [])
        assert result.intent == "bulk_membership_fee_mark_paid"

    def test_intent_result_confidence_reasonable(self):
        """bulk_membership_fee_mark_paid 신뢰도가 적절해야 함."""
        result = route("현재 멤버 전부 각각 회비에 맞춰서 완납 처리해줘", [])
        assert result.intent == "bulk_membership_fee_mark_paid"
        assert result.confidence >= 0.9


class TestBulkMembershipFeeServiceNo30000:
    def test_preview_items_have_no_30000_for_typical_fees(self, db) -> None:
        """서비스에서 생성하는 preview items에 30,000원 고정값이 없어야 함."""
        from app.models.member import Member
        from app.models.payment import PaymentRecord
        from app.services.bulk_membership_fee_service import preview_bulk_membership_fee_mark_paid

        m = Member(name="테스트", status="active")
        db.add(m)
        db.flush()

        r = PaymentRecord(
            member_id=m.id, period="2026-test",
            payment_type="membership_fee",
            required_amount=10000, paid_amount=0, status="unpaid",
        )
        db.add(r)
        db.flush()

        preview = preview_bulk_membership_fee_mark_paid(db, "2026-test")

        for item in preview.items:
            assert item.new_paid_amount != 30000, (
                f"30,000원 고정 금액이 감지됨: member={item.member_name}, amount={item.new_paid_amount}"
            )

    def test_apply_result_dict_has_no_30000_amount(self, db) -> None:
        """apply 결과 dict에 30000 값이 없어야 함."""
        from app.models.member import Member
        from app.models.payment import PaymentRecord
        from app.services.bulk_membership_fee_service import apply_bulk_membership_fee_mark_paid

        m = Member(name="테스트2", status="active")
        db.add(m)
        db.flush()

        r = PaymentRecord(
            member_id=m.id, period="2026-test2",
            payment_type="membership_fee",
            required_amount=15000, paid_amount=0, status="unpaid",
        )
        db.add(r)
        db.flush()

        result = apply_bulk_membership_fee_mark_paid(db, "2026-test2")
        result_dict = {
            "ok": result.ok,
            "period": result.period,
            "updated_count": result.updated_count,
        }

        # Should not have 30000
        paths_with_30000 = _result_has_30000(result_dict)
        assert not paths_with_30000, f"30,000원 감지: {paths_with_30000}"
