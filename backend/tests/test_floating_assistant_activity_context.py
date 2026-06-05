from app.services import assistant_query_service as svc


def test_activity_detail_context_uses_current_activity(monkeypatch):
    called = {}

    def fake_insight(db, activity_id):
        called["activity_id"] = str(activity_id)
        return {
            "activity_id": str(activity_id),
            "title": "향수 만들기",
            "activity_date": "2026-06-03",
            "location": "A401",
            "participant_count": 7,
            "fee_required": 70000,
            "fee_paid": 70000,
            "unpaid_count": 0,
            "report_status": "written",
            "evidence_status": "linked",
            "target_url": f"/activities/{activity_id}",
        }

    monkeypatch.setattr("app.services.assistant_activity_insight_service.get_activity_detail_insight", fake_insight)

    response = svc.answer_floating_assistant_chat(
        None,
        message="참여자 몇 명이야?",
        context={
            "page": "activity_detail",
            "activity_id": "11111111-1111-1111-1111-111111111111",
        },
    )

    assert response["intent"] == "activity_detail_insight"
    assert called["activity_id"] == "11111111-1111-1111-1111-111111111111"
    assert "7명" in response["answer"]


def test_global_participant_question_asks_for_activity_selection(monkeypatch):
    monkeypatch.setattr("app.services.assistant_activity_insight_service.find_activity_candidates", lambda db, message: [])

    response = svc.answer_floating_assistant_chat(None, message="참여자 몇 명이야?")

    assert response["intent"] == "activity_detail_insight"
    assert "활동명" in response["answer"]
    assert response["links"][0]["url"] == "/activities"


def test_named_activity_question_can_resolve_activity(monkeypatch):
    monkeypatch.setattr(
        "app.services.assistant_activity_insight_service.find_activity_candidates",
        lambda db, message: [{"activity_id": "11111111-1111-1111-1111-111111111111", "title": "향수 활동", "target_url": "/activities/11111111-1111-1111-1111-111111111111"}],
    )
    monkeypatch.setattr(
        "app.services.assistant_activity_insight_service.get_activity_detail_insight",
        lambda db, activity_id: {
            "activity_id": str(activity_id),
            "title": "향수 활동",
            "activity_date": "2026-06-03",
            "location": None,
            "participant_count": 5,
            "fee_required": 50000,
            "fee_paid": 50000,
            "unpaid_count": 0,
            "report_status": "written",
            "evidence_status": "linked",
            "target_url": f"/activities/{activity_id}",
        },
    )

    response = svc.answer_floating_assistant_chat(None, message="향수 활동에 몇 명 참여했어?")

    assert response["intent"] == "activity_detail_insight"
    assert "향수 활동" in response["answer"]
    assert "5명" in response["answer"]
