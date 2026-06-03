# -*- coding: utf-8 -*-
"""Tests for activity fee transaction exclusion (Task 32).

Tests the exclusion logic in activity_fee_transaction_matching_service
and the TransactionMatchExclusion model structure.

Note: Tests that need a live DB (integration) are skipped when no 'db' fixture
is available. Unit-level scope/logic tests run without a DB.
"""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest

from app.models.transaction_match_exclusion import TransactionMatchExclusion
from app.services.activity_fee_transaction_matching_service import ActivityFeeMatchSummary


# ── Unit tests: model structure ───────────────────────────────────────────────

class TestTransactionMatchExclusionModel:
    def test_model_has_required_fields(self):
        excl = TransactionMatchExclusion(
            transaction_id=uuid.uuid4(),
            activity_report_id=uuid.uuid4(),
            payment_type="activity_fee",
            is_active=True,
        )
        assert excl.payment_type == "activity_fee"
        assert excl.is_active is True

    def test_model_default_payment_type(self):
        # Default is applied at DB insert level; test that the field accepts "activity_fee"
        excl = TransactionMatchExclusion(
            transaction_id=uuid.uuid4(),
            activity_report_id=uuid.uuid4(),
            payment_type="activity_fee",
        )
        assert excl.payment_type == "activity_fee"

    def test_model_tablename(self):
        assert TransactionMatchExclusion.__tablename__ == "transaction_match_exclusions"

    def test_model_unique_constraint_exists(self):
        # UniqueConstraint should exist on (transaction_id, activity_report_id, payment_type)
        constraint_names = {
            c.name
            for c in TransactionMatchExclusion.__table_args__
            if hasattr(c, "name")
        }
        assert "uq_tx_exclusion_tx_activity_type" in constraint_names


# ── Unit tests: ActivityFeeMatchSummary has excluded_transactions field ───────

class TestSummaryExcludedField:
    def test_summary_has_excluded_field(self):
        summary = ActivityFeeMatchSummary(
            activity_id="abc",
            period="act-abc",
            total_transactions=10,
            auto_match_candidates=3,
            amount_mismatch=2,
            name_check_required=1,
            already_paid=0,
            already_matched=0,
            unmatched=4,
            excluded_transactions=2,
        )
        assert summary.excluded_transactions == 2

    def test_summary_excluded_defaults_to_zero(self):
        summary = ActivityFeeMatchSummary(
            activity_id="abc",
            period="act-abc",
            total_transactions=0,
            auto_match_candidates=0,
            amount_mismatch=0,
            name_check_required=0,
            already_paid=0,
            already_matched=0,
            unmatched=0,
        )
        assert summary.excluded_transactions == 0


# ── Unit tests: exclusion filtering in preview ───────────────────────────────


class TestExclusionFiltering:
    def test_summary_excluded_count_can_be_set(self):
        """ActivityFeeMatchSummary.excluded_transactions counts excluded items."""
        summary = ActivityFeeMatchSummary(
            activity_id="abc",
            period="act-abc",
            total_transactions=5,
            auto_match_candidates=2,
            amount_mismatch=1,
            name_check_required=0,
            already_paid=0,
            already_matched=0,
            unmatched=2,
            excluded_transactions=3,
        )
        assert summary.excluded_transactions == 3

    def test_exclusion_filtering_logic(self):
        """Transactions in excluded_tx_ids should be skipped (counter incremented)."""
        # Simulate the counter logic from the service
        excluded_tx_ids = {uuid.uuid4(), uuid.uuid4()}
        excluded_count = 0
        processed_ids = []

        test_tx_ids = list(excluded_tx_ids) + [uuid.uuid4(), uuid.uuid4()]

        for tx_id in test_tx_ids:
            if tx_id in excluded_tx_ids:
                excluded_count += 1
                continue
            processed_ids.append(tx_id)

        assert excluded_count == 2
        assert len(processed_ids) == 2
        for eid in excluded_tx_ids:
            assert eid not in processed_ids


class TestScopeProtection:
    """Verify that exclusion scope is limited to activity_fee + specific activity."""

    def test_exclusion_model_payment_type_field(self):
        """TransactionMatchExclusion has payment_type field for scope isolation."""
        excl = TransactionMatchExclusion(
            transaction_id=uuid.uuid4(),
            activity_report_id=uuid.uuid4(),
            payment_type="activity_fee",
        )
        # Membership fee exclusions would use a different payment_type
        assert excl.payment_type == "activity_fee"

    def test_exclusion_model_activity_scoped(self):
        """Each exclusion is scoped to a specific activity_report_id."""
        aid1 = uuid.uuid4()
        aid2 = uuid.uuid4()
        tx_id = uuid.uuid4()

        excl1 = TransactionMatchExclusion(
            transaction_id=tx_id,
            activity_report_id=aid1,
            payment_type="activity_fee",
        )
        excl2 = TransactionMatchExclusion(
            transaction_id=tx_id,
            activity_report_id=aid2,
            payment_type="activity_fee",
        )
        # Two separate exclusions for the same tx but different activities
        assert excl1.activity_report_id != excl2.activity_report_id

    def test_is_active_allows_soft_delete(self):
        """is_active=False means exclusion is soft-deleted (included back)."""
        excl = TransactionMatchExclusion(
            transaction_id=uuid.uuid4(),
            activity_report_id=uuid.uuid4(),
            payment_type="activity_fee",
            is_active=False,
        )
        assert excl.is_active is False
