from app.services import assistant_query_service as svc


def test_member_count_answer_uses_member_summary(monkeypatch):
    monkeypatch.setattr(
        svc,
        "get_member_summary",
        lambda db: {"total_members": 12, "active_members": 10},
    )

    response = svc.answer_floating_assistant_chat(None, message="총 부원 몇 명이야?")

    assert response["intent"] == "member_count"
    assert "12명" in response["answer"]
    assert "10명" in response["answer"]
    assert response["data_sources"] == ["members"]


def test_membership_fee_answer_uses_payment_records(monkeypatch):
    monkeypatch.setattr(
        "app.services.assistant_activity_insight_service.get_membership_fee_insight",
        lambda db, period=None: {
            "period": period,
            "total_count": 8,
            "unpaid_count": 3,
            "due_amount": 90000,
        },
    )

    response = svc.answer_floating_assistant_chat(
        None,
        message="회비 미납 몇 명이야?",
        context={"period": "2026-1"},
    )

    assert response["intent"] == "membership_fee_insight"
    assert "3명" in response["answer"]
    assert "90,000원" in response["answer"]
    assert response["links"][0]["url"] == "/payments"


def test_activity_fee_answer_returns_activity_links(monkeypatch):
    monkeypatch.setattr(
        "app.services.assistant_activity_insight_service.get_activity_fee_insight",
        lambda db, activity_id=None, period=None: {
            "activity_id": activity_id,
            "unpaid_count": 2,
            "due_amount": 40000,
            "activities": [
                {
                    "activity_id": "activity-1",
                    "activity_title": "향수 만들기",
                    "unpaid_count": 2,
                    "due_amount": 40000,
                    "target_url": "/activities/activity-1?tab=activity-fee",
                }
            ],
        },
    )

    response = svc.answer_floating_assistant_chat(
        None,
        message="활동비 미납 있는 활동 알려줘",
        context={"period": "2026-1"},
    )

    assert response["intent"] == "activity_fee_insight"
    assert response["links"][0]["url"] == "/activities/activity-1?tab=activity-fee"
