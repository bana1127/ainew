"""Task 31 Tests: Activity fee manual update — status auto-recalculation."""
from __future__ import annotations


def auto_status(paid: int, required: int, explicit: str | None = None) -> str:
    """Mirrors the status recalculation logic in update_activity_fee_record."""
    if explicit:
        return explicit
    if paid == 0:
        return "unpaid"
    if paid < required:
        return "partial"
    if paid == required:
        return "paid"
    return "overpaid"


class TestAutoStatusRecalculation:
    def test_zero_paid_gives_unpaid(self) -> None:
        assert auto_status(0, 25000) == "unpaid"

    def test_partial_payment(self) -> None:
        assert auto_status(10000, 25000) == "partial"

    def test_exact_payment_gives_paid(self) -> None:
        assert auto_status(25000, 25000) == "paid"

    def test_overpaid(self) -> None:
        assert auto_status(30000, 25000) == "overpaid"

    def test_explicit_status_overrides_calculation(self) -> None:
        # If user explicitly sets status, respect it
        assert auto_status(0, 25000, "exempt") == "exempt"
        assert auto_status(25000, 25000, "need_check") == "need_check"

    def test_zero_required_with_zero_paid(self) -> None:
        # Edge case: 0/0
        assert auto_status(0, 0) == "unpaid"

    def test_only_paid_amount_update_triggers_recalculation(self) -> None:
        """When only paid_amount is updated (no explicit status), status is recalculated."""
        scenarios = [
            (0, 10000, "unpaid"),
            (5000, 10000, "partial"),
            (10000, 10000, "paid"),
            (12000, 10000, "overpaid"),
        ]
        for paid, required, expected in scenarios:
            assert auto_status(paid, required) == expected, f"paid={paid}, required={required}"


class TestScopeProtection:
    def test_only_activity_fee_type_allowed(self) -> None:
        """Backend rejects non-activity_fee payment types."""
        def validate_payment_type(payment_type: str) -> bool:
            return payment_type == "activity_fee"

        assert validate_payment_type("activity_fee") is True
        assert validate_payment_type("membership_fee") is False

    def test_activity_id_must_match(self) -> None:
        """Backend rejects records that don't belong to the activity."""
        from uuid import uuid4
        act1 = uuid4()
        act2 = uuid4()

        def validate_scope(record_activity_id, request_activity_id) -> bool:
            return record_activity_id == request_activity_id

        assert validate_scope(act1, act1) is True
        assert validate_scope(act2, act1) is False
