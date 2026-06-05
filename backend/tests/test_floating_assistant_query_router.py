from app.services.assistant_query_service import route_floating_assistant_intent


def test_routes_member_count_question():
    assert route_floating_assistant_intent("총 부원 몇 명이야?") == "member_count"


def test_routes_activity_count_question():
    assert route_floating_assistant_intent("활동 몇 개 있어?") == "activity_overview"


def test_routes_activity_participant_question_with_named_activity():
    assert route_floating_assistant_intent("향수 활동에 몇 명 참여했어?") == "activity_detail_insight"


def test_routes_membership_fee_status_question():
    assert route_floating_assistant_intent("이번 학기 회비 미납 몇 명이야?") == "membership_fee_insight"


def test_routes_activity_fee_status_question():
    assert route_floating_assistant_intent("활동비 미납 있는 활동 알려줘") == "activity_fee_insight"
