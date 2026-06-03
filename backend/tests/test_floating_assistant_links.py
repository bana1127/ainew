from app.services.assistant_query_service import build_chat_response, link_for


def test_activity_fee_link_never_points_to_payments():
    url = link_for("activity_fee", "activity-1")

    assert url == "/activities/activity-1?tab=activity-fee"
    assert url != "/payments"


def test_membership_fee_link_points_to_payments():
    assert link_for("membership_fee") == "/payments"


def test_evidence_link_points_to_activity_evidence_tab():
    assert link_for("evidence", "activity-1") == "/activities/activity-1?tab=evidence"


def test_chat_response_keeps_structured_links_for_frontend():
    response = build_chat_response(
        answer="확인 필요",
        intent="evidence_missing",
        data_sources=["receipts"],
        links=[{"label": "증빙 탭", "url": "/activities/activity-1?tab=evidence"}],
    )

    assert response["links"] == [{"label": "증빙 탭", "url": "/activities/activity-1?tab=evidence"}]
