from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from uuid import uuid4

from app.services.ops_chatbot_query_service import _build_activity_rows


def test_activity_photo_missing_status_explains_not_required_before_threshold():
    activity = SimpleNamespace(
        id=uuid4(),
        title="Recent activity",
        status="completed",
        activity_date=date(2026, 6, 6),
        location=None,
        category_id=None,
        final_content="done",
        generated_content=None,
    )

    row = _build_activity_rows(
        [activity],
        [],
        [],
        [],
        {},
        photo_days_after=2,
        today=date(2026, 6, 7),
    )[0]

    assert row["activity_photo_required"] is False
    assert row["activity_photo_status"] == "아직 필수 시점 전"
    assert "활동 사진 업로드 확인" not in row["todo_items"]
