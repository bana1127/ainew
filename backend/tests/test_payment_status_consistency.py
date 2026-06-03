# -*- coding: utf-8 -*-
"""Tests for payment status calculation consistency (Task 40).

Verifies:
1. compute_status is deterministic from amounts
2. paid_amount == required_amount → always 'paid'
3. required_amount == 0 → always 'exempt'
4. Various amount combinations
5. Link policy: membership_fee → /payments, activity_fee → /activities/...
"""
from __future__ import annotations

import pytest

from app.services.payment_status_service import (
    compute_status,
    is_effectively_paid,
    severity_for_status,
    status_label,
)
from app.services.budget_service import target_url_for_payment_record


class TestComputeStatus:
    def test_required_zero_is_exempt(self):
        assert compute_status(0, 0) == "exempt"
        assert compute_status(1000, 0) == "exempt"

    def test_paid_zero_is_unpaid(self):
        assert compute_status(0, 10000) == "unpaid"

    def test_paid_equals_required_is_paid(self):
        assert compute_status(10000, 10000) == "paid"
        assert compute_status(15000, 15000) == "paid"

    def test_partial_payment(self):
        assert compute_status(5000, 10000) == "partial"
        assert compute_status(1, 10000) == "partial"

    def test_overpaid(self):
        assert compute_status(11000, 10000) == "overpaid"
        assert compute_status(20000, 10000) == "overpaid"

    def test_negative_values_treated_as_zero(self):
        # Negative amounts are clamped to 0
        assert compute_status(-100, 10000) == "unpaid"
        assert compute_status(10000, -100) == "exempt"

    def test_paid_status_not_affected_by_need_check(self):
        """compute_status is purely amount-based. need_check is NOT returned here."""
        assert compute_status(10000, 10000) == "paid"
        # need_check is manually assigned, never computed from amounts


class TestIsEffectivelyPaid:
    def test_paid_amount_equals_required(self):
        assert is_effectively_paid(10000, 10000, "paid") is True

    def test_status_paid_even_if_amount_slightly_off(self):
        assert is_effectively_paid(9999, 10000, "paid") is True

    def test_exempt_status(self):
        assert is_effectively_paid(0, 0, "exempt") is True
        assert is_effectively_paid(0, 10000, "exempt") is True

    def test_unpaid(self):
        assert is_effectively_paid(0, 10000, "unpaid") is False

    def test_partial(self):
        assert is_effectively_paid(5000, 10000, "partial") is False


class TestStatusLabel:
    def test_known_statuses(self):
        assert status_label("paid") == "납부 완료"
        assert status_label("unpaid") == "미납"
        assert status_label("partial") == "부분 납부"
        assert status_label("exempt") == "면제"
        assert status_label("need_check") == "확인 필요"
        assert status_label("overpaid") == "초과 납부"

    def test_unknown_status_returns_itself(self):
        assert status_label("custom_status") == "custom_status"


class TestSeverityForStatus:
    def test_danger_statuses(self):
        assert severity_for_status("unpaid") == "danger"
        assert severity_for_status("need_check") == "danger"

    def test_warning_statuses(self):
        assert severity_for_status("partial") == "warning"

    def test_success_statuses(self):
        assert severity_for_status("paid") == "success"
        assert severity_for_status("exempt") == "success"


class TestActivityFeePaidStatus:
    """Verify activity_fee paid_amount == required_amount is always 'paid'."""

    def test_activity_fee_full_payment_is_paid(self):
        """If paid_amount == required_amount, status must be 'paid', not 'need_check'."""
        status = compute_status(paid=25000, required=25000)
        assert status == "paid", (
            "paid_amount == required_amount must be 'paid', never 'need_check'"
        )

    def test_activity_fee_zero_required_is_exempt(self):
        status = compute_status(paid=0, required=0)
        assert status == "exempt"


class TestLinkPolicy:
    """Verify that target URLs follow the correct routing policy."""

    def test_membership_fee_links_to_payments(self):
        record = {
            "payment_type": "membership_fee",
            "activity_report_id": None,
        }
        url = target_url_for_payment_record(record)
        assert url == "/payments", f"membership_fee must link to /payments, got {url}"

    def test_activity_fee_links_to_activity_detail(self):
        import uuid
        activity_id = str(uuid.uuid4())
        record = {
            "payment_type": "activity_fee",
            "activity_report_id": activity_id,
        }
        url = target_url_for_payment_record(record)
        assert url == f"/activities/{activity_id}?tab=activity-fee", (
            f"activity_fee must link to activity detail, got {url}"
        )
        assert "/payments" not in url, "activity_fee must NOT link to /payments"

    def test_activity_fee_without_activity_id(self):
        record = {
            "payment_type": "activity_fee",
            "activity_report_id": None,
        }
        url = target_url_for_payment_record(record)
        assert "/payments" not in url, "activity_fee must NOT link to /payments even without activity_id"
