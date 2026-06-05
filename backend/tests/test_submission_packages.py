from __future__ import annotations

from datetime import date

from app.routers.submission_packages import _activities_in_month


class _FakeDb:
    def __init__(self) -> None:
        self.statement = None

    def scalars(self, statement):
        self.statement = statement
        return []


def test_activities_in_month_binds_date_values() -> None:
    db = _FakeDb()

    _activities_in_month(db, "2026-06")

    assert db.statement is not None
    params = db.statement.compile().params
    assert params["activity_date_1"] == date(2026, 6, 1)
    assert params["activity_date_2"] == date(2026, 6, 30)
