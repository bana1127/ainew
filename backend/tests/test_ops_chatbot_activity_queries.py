from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from uuid import uuid4

from app.services.ops_chatbot_query_service import _build_activity_rows


def _activity(title: str, *, status: str = "planned", activity_date: date | None = None):
    return SimpleNamespace(
        id=uuid4(),
        title=title,
        status=status,
        activity_date=activity_date,
        location="A401",
        category_id=None,
        final_content=None,
        generated_content=None,
    )


def test_activity_rows_include_planned_draft_and_completed_statuses():
    activities = [
        _activity("Planned activity", status="planned"),
        _activity("Draft activity", status="draft"),
        _activity("Completed activity", status="completed"),
    ]

    rows = _build_activity_rows(activities, [], [], [], {}, today=date(2026, 6, 7))

    assert len(rows) == 3
    assert {row["status"] for row in rows} == {"planned", "draft", "completed"}


def test_activity_row_contains_list_answer_fields():
    activity = _activity("Campus workshop", activity_date=date(2026, 5, 20))
    participant = SimpleNamespace(activity_report_id=activity.id)
    payment = SimpleNamespace(
        activity_report_id=activity.id,
        period="",
        status="paid",
        required_amount=10000,
        paid_amount=10000,
    )
    receipt = SimpleNamespace(
        activity_report_id=activity.id,
        document_type="receipt",
        need_check=False,
        evidence_status="valid",
    )

    row = _build_activity_rows([activity], [participant], [payment], [receipt], {}, today=date(2026, 6, 7))[0]

    assert row["title"] == "Campus workshop"
    assert row["activity_date"] == "2026-05-20"
    assert row["location"] == "A401"
    assert row["participant_count"] == 1
    assert row["activity_fee_status"] == "1/1 납부"
    assert row["evidence_count"] == 1
    assert row["target_url"].startswith("/activities/")
