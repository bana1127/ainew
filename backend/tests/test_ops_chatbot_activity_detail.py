from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from uuid import uuid4

from app.services.ops_chatbot_query_service import _build_activity_rows


def test_activity_detail_row_includes_fee_report_evidence_and_photo_status():
    activity = SimpleNamespace(
        id=uuid4(),
        title="Detail activity",
        status="generated",
        activity_date=date(2026, 6, 3),
        location="Lab",
        category_id=None,
        final_content="final report",
        generated_content=None,
    )
    payments = [
        SimpleNamespace(activity_report_id=activity.id, period="", status="paid", required_amount=10000, paid_amount=10000),
        SimpleNamespace(activity_report_id=activity.id, period="", status="unpaid", required_amount=10000, paid_amount=0),
    ]
    receipts = [
        SimpleNamespace(activity_report_id=activity.id, document_type="receipt", need_check=False, evidence_status="valid"),
        SimpleNamespace(activity_report_id=activity.id, document_type="activity_photo", need_check=False, evidence_status="valid"),
    ]

    row = _build_activity_rows([activity], [], payments, receipts, {}, today=date(2026, 6, 7))[0]

    assert row["activity_fee_total_count"] == 2
    assert row["activity_fee_unpaid_count"] == 1
    assert row["report_status"] == "작성됨"
    assert row["evidence_count"] == 2
    assert row["activity_photo_status"] == "업로드됨"
    assert row["activity_fee_url"].endswith("?tab=activity-fee")
    assert row["evidence_url"].endswith("?tab=evidence")
