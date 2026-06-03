# -*- coding: utf-8 -*-
"""Tests for budget review items policy (Task 40).

Verifies:
1. Individual membership_fee unpaid records do NOT appear as individual rows
2. membership_fee unpaid is aggregated as a single summary item
3. activity_fee unpaid is aggregated per activity (not per-member rows)
4. activity_fee target_url points to /activities/{id}?tab=activity-fee
5. membership_fee target_url is /payments
6. Other review items (transactions, receipts, budget overrun) are unaffected
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.services.budget_review_service import build_review_items


def _make_payment_record(
    id_: str,
    payment_type: str,
    status: str,
    required: int,
    paid: int,
    period: str = "2026-1",
    member_name: str = "테스트",
    activity_report_id: str | None = None,
):
    r = MagicMock()
    r.id = id_
    r.payment_type = payment_type
    r.status = status
    r.required_amount = required
    r.paid_amount = paid
    r.period = period
    r.member_name = member_name
    r.member_id = f"m-{id_}"
    r.activity_report_id = activity_report_id
    r.refund_status = None
    r.refund_amount = 0
    return r


class TestMembershipFeeNotIndividualRows:
    def test_membership_fee_unpaid_not_in_individual_rows(self):
        """Individual membership_fee unpaid records must NOT appear as individual rows."""
        records = [
            _make_payment_record("r1", "membership_fee", "unpaid", 15000, 0),
            _make_payment_record("r2", "membership_fee", "unpaid", 10000, 0),
            _make_payment_record("r3", "membership_fee", "unpaid", 10000, 0),
        ]
        items = build_review_items(
            payment_records=records,
            transactions=[],
            receipts=[],
            budget_rows=[],
            period="2026-1",
        )

        # No individual membership_fee_unpaid rows
        individual_rows = [i for i in items if i["type"] == "membership_fee_unpaid"]
        assert len(individual_rows) == 0, (
            "Individual membership_fee_unpaid rows should not appear in review items"
        )

    def test_membership_fee_summary_item_appears(self):
        """A single membership_fee_summary item should appear."""
        records = [
            _make_payment_record("r1", "membership_fee", "unpaid", 15000, 0),
            _make_payment_record("r2", "membership_fee", "unpaid", 10000, 0),
        ]
        items = build_review_items(
            payment_records=records,
            transactions=[],
            receipts=[],
            budget_rows=[],
            period="2026-1",
        )

        summary = [i for i in items if i["type"] == "membership_fee_summary"]
        assert len(summary) == 1, "Exactly one membership_fee_summary item should appear"
        assert summary[0]["amount"] == 25000
        assert summary[0]["target_url"] == "/payments"

    def test_membership_fee_all_paid_no_summary(self):
        """No summary item when all membership_fee records are paid."""
        records = [
            _make_payment_record("r1", "membership_fee", "paid", 15000, 15000),
            _make_payment_record("r2", "membership_fee", "paid", 10000, 10000),
        ]
        items = build_review_items(
            payment_records=records,
            transactions=[],
            receipts=[],
            budget_rows=[],
            period="2026-1",
        )
        summary = [i for i in items if i["type"] == "membership_fee_summary"]
        assert len(summary) == 0


class TestActivityFeeAggregation:
    def test_activity_fee_not_individual_rows(self):
        """activity_fee unpaid must NOT appear as individual member rows."""
        act_id = "activity-001"
        records = [
            _make_payment_record("r1", "activity_fee", "unpaid", 10000, 0, activity_report_id=act_id),
            _make_payment_record("r2", "activity_fee", "unpaid", 10000, 0, activity_report_id=act_id),
        ]
        items = build_review_items(
            payment_records=records,
            transactions=[],
            receipts=[],
            budget_rows=[],
            period="2026-1",
        )

        individual_rows = [i for i in items if i["type"] == "activity_fee_unpaid"]
        assert len(individual_rows) == 0, "Individual activity_fee_unpaid rows should not appear"

    def test_activity_fee_summary_per_activity(self):
        """activity_fee unpaid is aggregated per activity."""
        act_id = "activity-001"
        records = [
            _make_payment_record("r1", "activity_fee", "unpaid", 10000, 0, activity_report_id=act_id),
            _make_payment_record("r2", "activity_fee", "unpaid", 10000, 0, activity_report_id=act_id),
        ]
        items = build_review_items(
            payment_records=records,
            transactions=[],
            receipts=[],
            budget_rows=[],
            period="2026-1",
        )

        summary = [i for i in items if i["type"] == "activity_fee_summary"]
        assert len(summary) == 1
        assert summary[0]["amount"] == 20000
        assert f"/activities/{act_id}?tab=activity-fee" in summary[0]["target_url"]

    def test_activity_fee_target_url_not_payments(self):
        """activity_fee target_url must NOT go to /payments."""
        act_id = "activity-abc"
        records = [
            _make_payment_record("r1", "activity_fee", "unpaid", 10000, 0, activity_report_id=act_id),
        ]
        items = build_review_items(
            payment_records=records,
            transactions=[],
            receipts=[],
            budget_rows=[],
        )
        for item in items:
            if "activity_fee" in item.get("type", ""):
                assert "/payments" not in item["target_url"], (
                    "activity_fee items must not link to /payments"
                )

    def test_two_activities_two_summaries(self):
        """Two different activities produce two summary items."""
        records = [
            _make_payment_record("r1", "activity_fee", "unpaid", 10000, 0, activity_report_id="act-1"),
            _make_payment_record("r2", "activity_fee", "unpaid", 10000, 0, activity_report_id="act-2"),
        ]
        items = build_review_items(
            payment_records=records,
            transactions=[],
            receipts=[],
            budget_rows=[],
        )
        summaries = [i for i in items if i["type"] == "activity_fee_summary"]
        assert len(summaries) == 2


class TestPeriodFiltering:
    def test_period_filter_excludes_wrong_period(self):
        records = [
            _make_payment_record("r1", "membership_fee", "unpaid", 15000, 0, period="2026-1"),
            _make_payment_record("r2", "membership_fee", "unpaid", 15000, 0, period="2025-2"),
        ]
        items = build_review_items(
            payment_records=records,
            transactions=[],
            receipts=[],
            budget_rows=[],
            period="2026-1",
        )
        summary = [i for i in items if i["type"] == "membership_fee_summary"]
        assert len(summary) == 1
        assert summary[0]["amount"] == 15000  # Only 2026-1 period


class TestOtherItemsUnaffected:
    def test_transaction_review_items_still_appear(self):
        """Other review item types (transactions) are not affected by the change."""
        tx = MagicMock()
        tx.id = "tx-001"
        tx.payment_type = None
        tx.match_status = "unmatched"
        tx.withdraw_amount = 50000
        tx.deposit_amount = 0
        tx.memo = "테스트 거래"
        tx.transaction_datetime = None
        tx.linked_activity_id = None
        tx.review_status = "open"

        items = build_review_items(
            payment_records=[],
            transactions=[tx],
            receipts=[],
            budget_rows=[],
        )
        assert any(i["type"] == "unclassified_transaction" for i in items)

    def test_budget_overrun_still_appears(self):
        """Budget overrun items are not affected."""
        items = build_review_items(
            payment_records=[],
            transactions=[],
            receipts=[],
            budget_rows=[{
                "over_budget": True,
                "category_id": "cat-1",
                "category_name": "재료비",
                "difference_amount": -50000,
            }],
        )
        assert any(i["type"] == "budget_overrun" for i in items)
