from __future__ import annotations

from app.services.ops_chatbot_query_service import classify_ops_chatbot_intent


def test_membership_fee_question_routes_to_membership_summary():
    assert classify_ops_chatbot_intent("이번 학기 회비 납부 현황 알려줘") == "membership_fee_summary"


def test_unpaid_members_question_routes_to_unpaid_members():
    assert classify_ops_chatbot_intent("회비 미납 부원 알려줘") == "unpaid_members"


def test_budget_question_routes_to_budget_summary():
    assert classify_ops_chatbot_intent("이번 분기 수입 지출 알려줘", {"current_page": "budget"}) == "budget_summary"


def test_activity_fee_question_routes_to_activity_fee_status():
    assert classify_ops_chatbot_intent("활동비 미납 있는 활동 알려줘") == "activity_fee_status"
