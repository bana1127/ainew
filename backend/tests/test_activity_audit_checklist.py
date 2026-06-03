# -*- coding: utf-8 -*-
"""Tests for activity audit checklist service (Task 34).

All tests are unit-level and work without a live DB by testing the service
logic directly with mock objects.

Tests cover:
1. Checklist items have correct keys
2. basic_info check fires when fields are missing
3. HWPX check fires when no HWPX file exists
4. Evidence receipt check works
5. ready_for_audit is True only when all items done
6. compute_audit_checklist returns correct total_done/total_items
"""
from __future__ import annotations

import uuid
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from app.services.activity_audit_check_service import (
    AuditCheckItem,
    ActivityAuditCheckResult,
    compute_audit_checklist,
)


# ── Structure tests (no DB needed) ────────────────────────────────────────────

class TestAuditCheckItem:
    def test_check_item_has_required_fields(self):
        item = AuditCheckItem(key="test", label="테스트", done=True)
        assert item.key == "test"
        assert item.label == "테스트"
        assert item.done is True
        assert item.detail is None
        assert item.count is None
        assert item.warning is None

    def test_check_item_not_done(self):
        item = AuditCheckItem(
            key="hwpx_generated",
            label="HWPX 생성",
            done=False,
            warning="보고서 탭에서 HWPX 생성 필요",
        )
        assert item.done is False
        assert item.warning is not None


class TestActivityAuditCheckResult:
    def test_result_has_required_fields(self):
        result = ActivityAuditCheckResult(
            activity_id="abc",
            activity_title="테스트 활동",
            items=[AuditCheckItem(key="a", label="A", done=True)],
            total_done=1,
            total_items=1,
            ready_for_audit=True,
        )
        assert result.ready_for_audit is True
        assert len(result.items) == 1

    def test_not_ready_when_items_missing(self):
        result = ActivityAuditCheckResult(
            activity_id="abc",
            activity_title="테스트 활동",
            items=[
                AuditCheckItem(key="a", label="A", done=True),
                AuditCheckItem(key="b", label="B", done=False),
            ],
            total_done=1,
            total_items=2,
            ready_for_audit=False,
        )
        assert result.ready_for_audit is False
        assert result.total_done == 1


# ── compute_audit_checklist mock tests ────────────────────────────────────────

def _make_report(title="테스트 활동", activity_date=date(2026, 6, 1), location="동아리방",
                 final_content=None, generated_content=None):
    from app.models.activity import ActivityReport
    r = MagicMock(spec=ActivityReport)
    r.title = title
    r.activity_date = activity_date
    r.location = location
    r.final_content = final_content
    r.generated_content = generated_content
    r.id = uuid.uuid4()
    return r


def _make_db(report, participants=None, hwpx_files=None, receipts=None, fee_records=None):
    db = MagicMock()
    db.get.return_value = report

    participants = participants or []
    hwpx_files = hwpx_files or []
    receipts = receipts or []
    fee_records = fee_records or []

    call_count = [0]

    def scalars_side_effect(stmt):
        call_count[0] += 1
        result = MagicMock()
        if call_count[0] == 1:
            result.__iter__ = MagicMock(return_value=iter(participants))
        elif call_count[0] == 2:
            result.__iter__ = MagicMock(return_value=iter(hwpx_files))
        elif call_count[0] == 3:
            result.__iter__ = MagicMock(return_value=iter(receipts))
        elif call_count[0] == 4:
            result.__iter__ = MagicMock(return_value=iter(fee_records))
        else:
            result.__iter__ = MagicMock(return_value=iter([]))
        return result

    db.scalars.side_effect = scalars_side_effect
    return db


class TestComputeAuditChecklist:
    def test_all_done_when_everything_present(self):
        from app.models.activity import ActivityParticipant
        from app.models.file import UploadedFile
        from app.models.receipt import Receipt
        from app.models.payment import PaymentRecord

        report = _make_report(final_content="보고서 내용")

        participant = MagicMock(spec=ActivityParticipant)
        hwpx = MagicMock(spec=UploadedFile)
        receipt = MagicMock(spec=Receipt)
        receipt.evidence_status = "valid"
        fee = MagicMock(spec=PaymentRecord)
        fee.status = "paid"

        db = _make_db(report, [participant], [hwpx], [receipt], [fee])
        result = compute_audit_checklist(db, report.id)

        assert result.total_items == 7
        assert result.total_done == 7
        assert result.ready_for_audit is True

    def test_basic_info_fails_without_date(self):
        report = _make_report(activity_date=None)
        db = _make_db(report)
        result = compute_audit_checklist(db, report.id)

        basic_item = next(i for i in result.items if i.key == "basic_info")
        assert basic_item.done is False
        assert basic_item.detail is not None
        assert "활동 일자" in basic_item.detail

    def test_hwpx_check_fails_when_no_hwpx(self):
        report = _make_report()
        db = _make_db(report, hwpx_files=[])
        result = compute_audit_checklist(db, report.id)

        hwpx_item = next(i for i in result.items if i.key == "hwpx_generated")
        assert hwpx_item.done is False
        assert hwpx_item.warning is not None

    def test_hwpx_check_passes_when_hwpx_present(self):
        from app.models.file import UploadedFile
        report = _make_report()
        hwpx = MagicMock(spec=UploadedFile)
        db = _make_db(report, hwpx_files=[hwpx])
        result = compute_audit_checklist(db, report.id)

        hwpx_item = next(i for i in result.items if i.key == "hwpx_generated")
        assert hwpx_item.done is True

    def test_receipts_analyzed_fails_with_pending(self):
        from app.models.receipt import Receipt
        report = _make_report()
        receipt = MagicMock(spec=Receipt)
        receipt.evidence_status = "pending"
        db = _make_db(report, receipts=[receipt])
        result = compute_audit_checklist(db, report.id)

        analyzed_item = next(i for i in result.items if i.key == "receipts_analyzed")
        assert analyzed_item.done is False
        assert analyzed_item.detail is not None

    def test_report_body_fails_without_content(self):
        report = _make_report(final_content=None, generated_content=None)
        db = _make_db(report)
        result = compute_audit_checklist(db, report.id)

        report_item = next(i for i in result.items if i.key == "report_body")
        assert report_item.done is False

    def test_not_found_raises(self):
        db = MagicMock()
        db.get.return_value = None
        with pytest.raises(ValueError, match="Activity not found"):
            compute_audit_checklist(db, uuid.uuid4())

    def test_checklist_has_seven_items(self):
        report = _make_report()
        db = _make_db(report)
        result = compute_audit_checklist(db, report.id)
        assert result.total_items == 7

    def test_all_required_keys_present(self):
        report = _make_report()
        db = _make_db(report)
        result = compute_audit_checklist(db, report.id)
        keys = {item.key for item in result.items}
        expected_keys = {
            "basic_info", "participants", "report_body",
            "hwpx_generated", "evidence_receipts",
            "receipts_analyzed", "activity_fee",
        }
        assert expected_keys == keys
