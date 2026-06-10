from __future__ import annotations

from app.services.ops_chatbot_query_service import classify_ops_chatbot_intent


def test_current_activity_context_routes_this_activity_fee_question():
    intent = classify_ops_chatbot_intent(
        "이 활동 활동비 얼마나 납부됐어?",
        {
            "current_page": "activity_detail",
            "current_activity_id": "11111111-1111-1111-1111-111111111111",
            "current_tab": "activity-fee",
        },
    )

    assert intent == "activity_fee_status"


def test_activity_detail_context_routes_generic_this_activity_question():
    intent = classify_ops_chatbot_intent(
        "이 활동 정보 알려줘",
        {
            "current_page": "activity_detail",
            "current_activity_id": "11111111-1111-1111-1111-111111111111",
        },
    )

    assert intent == "activity_detail"
