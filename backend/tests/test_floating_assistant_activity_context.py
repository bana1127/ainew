from app.services import assistant_query_service as svc


def test_activity_detail_context_uses_current_activity(monkeypatch):
    called = {}

    def fake_count(db, *, activity_id):
        called["activity_id"] = str(activity_id)
        return {
            "activity_id": str(activity_id),
            "activity_title": "향수 만들기",
            "participant_count": 7,
        }

    monkeypatch.setattr(svc, "get_activity_participant_count", fake_count)

    response = svc.answer_floating_assistant_chat(
        None,
        message="참여자 몇 명이야?",
        context={
            "page": "activity_detail",
            "activity_id": "11111111-1111-1111-1111-111111111111",
        },
    )

    assert response["intent"] == "activity_participant_count"
    assert called["activity_id"] == "11111111-1111-1111-1111-111111111111"
    assert "7명" in response["answer"]


def test_global_participant_question_asks_for_activity_selection(monkeypatch):
    monkeypatch.setattr(svc, "find_activity_from_message", lambda db, message: None)

    response = svc.answer_floating_assistant_chat(None, message="참여자 몇 명이야?")

    assert response["intent"] == "activity_participant_count"
    assert "활동을 먼저 선택" in response["answer"]
    assert response["links"][0]["url"] == "/activities"


def test_named_activity_question_can_resolve_activity(monkeypatch):
    class Activity:
        id = "activity-1"

    monkeypatch.setattr(svc, "find_activity_from_message", lambda db, message: Activity())
    monkeypatch.setattr(
        svc,
        "get_activity_participant_count",
        lambda db, *, activity_id: {
            "activity_id": activity_id,
            "activity_title": "향수 활동",
            "participant_count": 5,
        },
    )

    response = svc.answer_floating_assistant_chat(None, message="향수 활동에 몇 명 참여했어?")

    assert response["intent"] == "activity_participant_count"
    assert "향수 활동" in response["answer"]
    assert "5명" in response["answer"]
