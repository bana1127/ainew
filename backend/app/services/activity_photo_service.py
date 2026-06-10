from __future__ import annotations

from datetime import date, timedelta


def is_activity_photo_required(
    activity_date: date | None,
    days_after: int,
    today: date | None = None,
) -> bool:
    if activity_date is None:
        return False
    today = today or date.today()
    return today >= activity_date + timedelta(days=days_after)


def build_activity_photo_checklist_item(
    photo_count: int,
    activity_date: date | None,
    days_after: int,
    today: date | None = None,
) -> dict:
    required = is_activity_photo_required(activity_date, days_after, today=today)
    detail = f"활동 후 {days_after}일 경과" if photo_count == 0 and required else None
    return {
        "key": "activity_photo",
        "label": "활동 사진 업로드",
        "done": photo_count > 0,
        "count": photo_count,
        "detail": detail,
    }
