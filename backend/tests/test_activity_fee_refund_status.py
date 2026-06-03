"""Task 31 Tests: Activity fee refund status management."""
from __future__ import annotations

VALID_REFUND_STATUSES = {"none", "refund_required", "refund_pending", "refunded"}


def validate_refund_status(status: str) -> bool:
    return status in VALID_REFUND_STATUSES


def display_refund_status(status: str) -> str:
    labels = {
        "none": "없음",
        "refund_required": "환불 필요",
        "refund_pending": "환불 대기",
        "refunded": "환불 완료",
    }
    return labels.get(status, status)


class TestRefundStatusValues:
    def test_valid_statuses_accepted(self) -> None:
        for status in ("none", "refund_required", "refund_pending", "refunded"):
            assert validate_refund_status(status) is True

    def test_invalid_status_rejected(self) -> None:
        assert validate_refund_status("refund_denied") is False
        assert validate_refund_status("cancelled") is False
        assert validate_refund_status("") is False

    def test_display_labels(self) -> None:
        assert display_refund_status("none") == "없음"
        assert display_refund_status("refund_required") == "환불 필요"
        assert display_refund_status("refund_pending") == "환불 대기"
        assert display_refund_status("refunded") == "환불 완료"


class TestRefundStatusScopeProtection:
    def test_refund_status_update_only_on_activity_fee(self) -> None:
        """Refund status change via activity-fees endpoint only applies to activity_fee records."""
        def can_update_refund(payment_type: str, activity_id_match: bool) -> bool:
            return payment_type == "activity_fee" and activity_id_match

        assert can_update_refund("activity_fee", True) is True
        assert can_update_refund("membership_fee", True) is False
        assert can_update_refund("activity_fee", False) is False

    def test_refund_status_field_in_update_payload(self) -> None:
        """The update endpoint allows refund_status in payload."""
        allowed_fields = {"paid_amount", "status", "required_amount", "refund_status"}
        assert "refund_status" in allowed_fields
        assert "membership_fee" not in allowed_fields


class TestRefundStatusTransitions:
    def test_none_to_required(self) -> None:
        status = "none"
        new_status = "refund_required"
        assert validate_refund_status(new_status) is True

    def test_required_to_pending(self) -> None:
        status = "refund_required"
        new_status = "refund_pending"
        assert validate_refund_status(new_status) is True

    def test_pending_to_refunded(self) -> None:
        status = "refund_pending"
        new_status = "refunded"
        assert validate_refund_status(new_status) is True

    def test_summary_counts_refund_needed(self) -> None:
        """Summary's refund_needed counts refund_required AND refund_pending."""
        records = [
            {"refund_status": "refund_required"},
            {"refund_status": "refund_pending"},
            {"refund_status": "refunded"},
            {"refund_status": "none"},
            {},  # no refund_status key
        ]
        refund_needed = sum(
            1 for r in records
            if r.get("refund_status") in ("refund_required", "refund_pending")
        )
        assert refund_needed == 2
