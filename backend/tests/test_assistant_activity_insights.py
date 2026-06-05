from __future__ import annotations

from app.services import assistant_query_service as svc


def test_activity_overview_intent_for_activity_count():
    assert svc.route_floating_assistant_intent("활동이 몇 개 있어?") == "activity_overview"


def test_activity_overview_answer(monkeypatch):
    monkeypatch.setattr(
        "app.services.assistant_activity_insight_service.get_activity_overview",
        lambda db, period=None: {
            "total_count": 2,
            "items": [
                {
                    "activity_id": "activity-1",
                    "title": "위퍼퓸 교내조향활동",
                    "activity_date": "2026-06-03",
                    "participant_count": 20,
                    "target_url": "/activities/activity-1",
                }
            ],
        },
    )

    response = svc.answer_floating_assistant_chat(None, message="각각 어떤 활동이었어?")

    assert response["intent"] == "activity_overview"
    assert "2개" in response["answer"]
    assert response["links"][0]["url"] == "/activities/activity-1"


def test_activity_fee_followup_uses_last_activity_id(monkeypatch):
    seen = {}

    def fake_fee(db, *, activity_id=None, period=None):
        seen["activity_id"] = str(activity_id)
        return {
            "activity_id": str(activity_id),
            "total_records": 2,
            "unpaid_count": 1,
            "due_amount": 10000,
            "activities": [
                {
                    "activity_id": str(activity_id),
                    "activity_title": "위퍼퓸 교내조향활동",
                    "required_amount": 20000,
                    "paid_amount": 10000,
                    "unpaid_count": 1,
                    "due_amount": 10000,
                    "target_url": f"/activities/{activity_id}?tab=activity-fee",
                }
            ],
        }

    monkeypatch.setattr("app.services.assistant_activity_insight_service.get_activity_fee_insight", fake_fee)

    response = svc.answer_floating_assistant_chat(
        None,
        message="그 활동 활동비는?",
        context={"last_activity_id": "11111111-1111-1111-1111-111111111111"},
    )

    assert response["intent"] == "activity_fee_insight"
    assert seen["activity_id"] == "11111111-1111-1111-1111-111111111111"
    assert response["links"][0]["url"] == "/activities/11111111-1111-1111-1111-111111111111?tab=activity-fee"


def test_membership_fee_links_to_payments(monkeypatch):
    monkeypatch.setattr(
        "app.services.assistant_activity_insight_service.get_membership_fee_insight",
        lambda db, period=None: {
            "period": period,
            "total_count": 10,
            "unpaid_count": 3,
            "due_amount": 90000,
            "target_url": "/payments",
        },
    )

    response = svc.answer_floating_assistant_chat(None, message="회비 미납 몇 명이야?")

    assert response["intent"] == "membership_fee_insight"
    assert response["links"][0]["url"] == "/payments"


def test_calendar_schedule_answer(monkeypatch):
    monkeypatch.setattr(
        "app.services.assistant_activity_insight_service.get_calendar_schedule_summary",
        lambda db, period=None, event_type=None: {
            "period": period,
            "total_count": 2,
            "items": [
                {"event_type": "activity", "title": "조향활동", "date": "2026-06-03"},
                {"event_type": "deadline", "title": "회비 납부 마감", "date": "2026-06-05"},
            ],
            "target_url": "/dashboard",
        },
    )

    response = svc.answer_floating_assistant_chat(None, message="이번 주 일정 뭐 있어?")

    assert response["intent"] == "calendar_schedule"
    assert "2건" in response["answer"]
    assert response["links"][0]["url"] == "/dashboard"


def test_budget_insight_answer(monkeypatch):
    monkeypatch.setattr(
        "app.services.assistant_activity_insight_service.get_budget_insight",
        lambda db, period=None: {
            "period": period,
            "total_income": 100000,
            "total_expense": 35000,
            "net_change": 65000,
            "current_balance": 65000,
            "target_url": "/budget",
        },
    )

    response = svc.answer_floating_assistant_chat(None, message="이번 달 수입 지출 알려줘")

    assert response["intent"] == "budget_insight"
    assert "100,000원" in response["answer"]
    assert response["links"][0]["url"] == "/budget"
