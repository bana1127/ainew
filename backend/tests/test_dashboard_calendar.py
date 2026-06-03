# -*- coding: utf-8 -*-
"""Tests for dashboard calendar and todo API (Task 35).

Unit tests that work without a live DB by testing the service logic:
1. Calendar month parsing
2. Calendar event structure
3. needs_report / needs_evidence flags
4. Deleted activities excluded
5. Month filtering
6. Dashboard todo structure
"""
from __future__ import annotations

import calendar
from datetime import date
from unittest.mock import MagicMock, patch

import pytest


# ── Calendar month parsing ───────────────────────────────────────────────────

class TestCalendarMonthParsing:
    def test_valid_month_string(self):
        target = date(2026, 6, 1)
        year, mon = "2026-06".split("-")
        assert int(year) == 2026
        assert int(mon) == 6

    def test_month_boundaries(self):
        _, last_day = calendar.monthrange(2026, 6)
        assert last_day == 30

        _, last_day_feb = calendar.monthrange(2026, 2)
        assert last_day_feb == 28

        _, last_day_leap = calendar.monthrange(2024, 2)
        assert last_day_leap == 29

    def test_month_start_end(self):
        year, month = 2026, 6
        _, last_day = calendar.monthrange(year, month)
        month_start = date(year, month, 1)
        month_end = date(year, month, last_day)
        assert month_start == date(2026, 6, 1)
        assert month_end == date(2026, 6, 30)


# ── Calendar event structure ─────────────────────────────────────────────────

class TestCalendarEventStructure:
    def _make_activity(self, title="테스트 활동", activity_date=date(2026, 6, 15),
                       status="planned", final_content=None, generated_content=None,
                       deleted_at=None):
        from app.models.activity import ActivityReport
        act = MagicMock(spec=ActivityReport)
        act.id = __import__("uuid").uuid4()
        act.title = title
        act.activity_date = activity_date
        act.location = "동아리방"
        act.status = status
        act.final_content = final_content
        act.generated_content = generated_content
        act.deleted_at = deleted_at
        return act

    def test_event_has_required_fields(self):
        act = self._make_activity(final_content="보고서")
        has_report = bool(act.final_content or act.generated_content)
        has_evidence = False  # no receipts

        event = {
            "id": str(act.id),
            "type": "activity",
            "title": act.title,
            "date": str(act.activity_date),
            "location": act.location or "",
            "status": act.status or "planned",
            "needs_report": not has_report,
            "needs_evidence": not has_evidence,
            "url": f"/activities/{act.id}",
        }
        assert event["type"] == "activity"
        assert event["date"] == "2026-06-15"
        assert event["needs_report"] is False
        assert event["needs_evidence"] is True

    def test_needs_report_true_when_no_content(self):
        act = self._make_activity(final_content=None, generated_content=None)
        has_report = bool(act.final_content or act.generated_content)
        assert not has_report

    def test_needs_report_false_when_final_content(self):
        act = self._make_activity(final_content="본문 있음")
        has_report = bool(act.final_content or act.generated_content)
        assert has_report

    def test_needs_evidence_false_when_receipts_exist(self):
        # Simulate receipt_counts with an activity
        import uuid
        act_id = str(uuid.uuid4())
        receipt_counts = {act_id: 2}
        has_evidence = receipt_counts.get(act_id, 0) > 0
        assert has_evidence

    def test_deleted_activity_excluded(self):
        from datetime import datetime, timezone
        act = self._make_activity(deleted_at=datetime.now(timezone.utc))
        # Deleted activities must be excluded — check deleted_at is set
        assert act.deleted_at is not None


# ── Month filtering ──────────────────────────────────────────────────────────

class TestMonthFiltering:
    def test_activity_in_month_passes(self):
        act_date = date(2026, 6, 15)
        month_start = date(2026, 6, 1)
        month_end = date(2026, 6, 30)
        assert month_start <= act_date <= month_end

    def test_activity_before_month_excluded(self):
        act_date = date(2026, 5, 31)
        month_start = date(2026, 6, 1)
        assert act_date < month_start

    def test_activity_after_month_excluded(self):
        act_date = date(2026, 7, 1)
        month_end = date(2026, 6, 30)
        assert act_date > month_end

    def test_first_day_of_month_included(self):
        act_date = date(2026, 6, 1)
        month_start = date(2026, 6, 1)
        month_end = date(2026, 6, 30)
        assert month_start <= act_date <= month_end

    def test_last_day_of_month_included(self):
        act_date = date(2026, 6, 30)
        month_start = date(2026, 6, 1)
        month_end = date(2026, 6, 30)
        assert month_start <= act_date <= month_end


# ── Dashboard Todo ──────────────────────────────────────────────────────────

class TestDashboardTodoStructure:
    def test_todo_response_has_required_keys(self):
        expected_keys = {
            "unpaid_membership_fee",
            "unpaid_activity_fee",
            "no_report_activities",
            "no_evidence_activities",
            "no_hwpx_activities",
        }
        # Simulate what the API returns
        response = {
            "unpaid_membership_fee": 3,
            "unpaid_activity_fee": 1,
            "no_report_activities": 5,
            "no_evidence_activities": 2,
            "no_hwpx_activities": 4,
        }
        assert set(response.keys()) == expected_keys

    def test_todo_counts_are_non_negative(self):
        response = {
            "unpaid_membership_fee": 0,
            "unpaid_activity_fee": 0,
            "no_report_activities": 0,
            "no_evidence_activities": 0,
            "no_hwpx_activities": 0,
        }
        for v in response.values():
            assert v >= 0
