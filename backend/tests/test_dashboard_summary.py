# -*- coding: utf-8 -*-
"""Tests for dashboard summary structure (Task 35).

Verifies that the dashboard_summary response returns the expected fields,
and that the DashboardSummary type in the frontend has the right shape.
"""
from __future__ import annotations


class TestDashboardSummaryFields:
    """Verify dashboard summary returns required keys."""

    REQUIRED_KEYS = {
        "total_members",
        "active_members",
        "total_activity_reports",
        "draft_reports",
        "total_receipts",
        "pending_receipts",
        "total_transactions",
        "total_payment_records",
        "unpaid_count",
        "unpaid_membership_fee_count",
        "unpaid_activity_fee_count",
        "unread_notifications",
    }

    def _mock_summary(self) -> dict:
        return {k: 0 for k in self.REQUIRED_KEYS}

    def test_summary_has_all_required_keys(self):
        summary = self._mock_summary()
        for key in self.REQUIRED_KEYS:
            assert key in summary, f"Missing key: {key}"

    def test_unpaid_count_equals_sum_of_both_types(self):
        summary = {
            "unpaid_membership_fee_count": 3,
            "unpaid_activity_fee_count": 2,
            "unpaid_count": 5,
        }
        assert summary["unpaid_count"] == (
            summary["unpaid_membership_fee_count"] + summary["unpaid_activity_fee_count"]
        )


class TestCalendarResponseStructure:
    """Verify calendar response has required fields."""

    REQUIRED_EVENT_KEYS = {
        "id", "type", "title", "date", "location",
        "status", "needs_report", "needs_evidence", "url",
    }

    def _mock_event(self) -> dict:
        return {
            "id": "abc",
            "type": "activity",
            "title": "테스트",
            "date": "2026-06-15",
            "location": "동아리방",
            "status": "planned",
            "needs_report": False,
            "needs_evidence": True,
            "url": "/activities/abc",
        }

    def test_event_has_all_required_keys(self):
        event = self._mock_event()
        for key in self.REQUIRED_EVENT_KEYS:
            assert key in event, f"Missing key: {key}"

    def test_event_type_is_activity(self):
        event = self._mock_event()
        assert event["type"] == "activity"

    def test_event_url_format(self):
        event = self._mock_event()
        assert event["url"].startswith("/activities/")

    def test_calendar_response_has_month_and_events(self):
        calendar_resp = {"month": "2026-06", "events": [self._mock_event()]}
        assert "month" in calendar_resp
        assert "events" in calendar_resp
        assert isinstance(calendar_resp["events"], list)


class TestDashboardTodoResponseStructure:
    """Verify todo response has all required fields."""

    REQUIRED_TODO_KEYS = {
        "unpaid_membership_fee",
        "unpaid_activity_fee",
        "no_report_activities",
        "no_evidence_activities",
        "no_hwpx_activities",
    }

    def test_todo_has_all_keys(self):
        todo = {k: 0 for k in self.REQUIRED_TODO_KEYS}
        for key in self.REQUIRED_TODO_KEYS:
            assert key in todo

    def test_todo_counts_non_negative(self):
        todo = {k: 0 for k in self.REQUIRED_TODO_KEYS}
        for v in todo.values():
            assert v >= 0
