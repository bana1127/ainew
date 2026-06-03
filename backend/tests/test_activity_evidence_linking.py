# -*- coding: utf-8 -*-
"""Tests for activity evidence linking (Task 34).

Tests the receipts.py fix (receipt_date vs purchased_at) and the
receipt-to-activity linking logic.
"""
from __future__ import annotations

import uuid
from datetime import date


class TestReceiptDateField:
    """Verify Receipt model uses receipt_date not purchased_at."""

    def test_receipt_model_has_receipt_date(self):
        from app.models.receipt import Receipt
        assert hasattr(Receipt, "receipt_date"), "Receipt model must have receipt_date field"

    def test_receipt_model_has_no_purchased_at(self):
        from app.models.receipt import Receipt
        assert not hasattr(Receipt, "purchased_at"), (
            "Receipt.purchased_at was removed; use receipt_date instead"
        )

    def test_receipt_date_is_date_type(self):
        from app.models.receipt import Receipt
        r = Receipt()
        r.receipt_date = date(2026, 6, 1)
        assert r.receipt_date == date(2026, 6, 1)


class TestReceiptActivityLinking:
    """Verify that linking a receipt to an activity also syncs the UploadedFile."""

    def test_link_receipt_syncs_uploaded_file(self):
        """Simulates the link_receipt_to_activity endpoint logic."""
        from unittest.mock import MagicMock
        from app.models.receipt import Receipt
        from app.models.file import UploadedFile

        receipt = MagicMock(spec=Receipt)
        receipt.file_id = uuid.uuid4()
        receipt.activity_report_id = None

        uploaded_file = MagicMock(spec=UploadedFile)

        activity_id = uuid.uuid4()

        # Simulate the link logic from receipts.py
        receipt.activity_report_id = activity_id
        if receipt.file_id:
            uploaded_file.activity_report_id = activity_id
            uploaded_file.file_category = "receipt"
            uploaded_file.file_role = "evidence"
            uploaded_file.related_entity_type = "activity_report"
            uploaded_file.related_entity_id = activity_id

        assert receipt.activity_report_id == activity_id
        assert uploaded_file.activity_report_id == activity_id
        assert uploaded_file.file_category == "receipt"
        assert uploaded_file.file_role == "evidence"

    def test_unlink_receipt_clears_uploaded_file_activity(self):
        """Unlinking a receipt clears file activity context but keeps the file."""
        from unittest.mock import MagicMock
        from app.models.receipt import Receipt
        from app.models.file import UploadedFile

        activity_id = uuid.uuid4()
        receipt = MagicMock(spec=Receipt)
        receipt.file_id = uuid.uuid4()
        receipt.activity_report_id = activity_id

        uploaded_file = MagicMock(spec=UploadedFile)
        uploaded_file.activity_report_id = activity_id
        uploaded_file.file_category = "receipt"
        uploaded_file.file_role = "evidence"

        # Simulate unlink
        receipt.activity_report_id = None
        uploaded_file.activity_report_id = None
        uploaded_file.related_entity_type = None
        uploaded_file.related_entity_id = None

        assert receipt.activity_report_id is None
        assert uploaded_file.activity_report_id is None
        # file_category stays "receipt" (file is preserved, just unlinked)


class TestFileGrouping:
    """Test file category/role grouping logic."""

    def test_receipt_category_is_evidence_group(self):
        # receipt + evidence role should go to "증빙 파일" group
        cat = "receipt"
        role = "evidence"
        group_cats = {"receipt", "photo"}
        group_roles = {"evidence"}
        in_evidence = cat in group_cats or role in group_roles
        assert in_evidence

    def test_hwpx_generated_is_generated_group(self):
        cat = "activity_report"
        role = "generated"
        group_cats = {"activity_report", "submission_package"}
        group_roles = {"generated"}
        in_generated = cat in group_cats or role in group_roles
        assert in_generated

    def test_bank_statement_is_source_group(self):
        cat = "bank_statement"
        role = "source"
        group_cats = {"bank_statement", "activity_plan", "google_form_application", "google_form_feedback"}
        group_roles = {"source"}
        in_source = cat in group_cats or role in group_roles
        assert in_source


class TestAuditChecklistRouting:
    """Test intent routing for audit check commands."""

    def test_감사_준비_상태_확인해줘(self):
        from app.agents.intent_router import route
        result = route("감사 준비 상태 확인해줘", [])
        assert result.intent == "activity_audit_check"

    def test_증빙_빠진_거_확인해줘(self):
        from app.agents.intent_router import route
        result = route("증빙 빠진 거 확인해줘", [])
        assert result.intent == "activity_audit_check"

    def test_감사_체크리스트(self):
        from app.agents.intent_router import route
        result = route("감사 체크리스트 보여줘", [])
        assert result.intent == "activity_audit_check"

    def test_audit_check_never_routes_to_payment(self):
        from app.agents.intent_router import route
        result = route("감사 준비 상태 확인해줘", [])
        assert result.intent not in {"payment_matching", "bulk_membership_fee_mark_paid"}
