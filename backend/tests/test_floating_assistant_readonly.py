from app.services.assistant_query_service import answer_floating_assistant_chat, is_mutation_request


def test_mutation_request_is_detected():
    assert is_mutation_request("김민수 회비 완납 처리해줘")


def test_floating_assistant_does_not_modify_db_for_mutation_request():
    class FakeDb:
        touched = False

        def add(self, obj):
            self.touched = True

        def commit(self):
            self.touched = True

    db = FakeDb()

    response = answer_floating_assistant_chat(db, message="김민수 회비 완납 처리해줘")

    assert db.touched is False
    assert response["intent"] == "unknown"
    assert "조회 전용" in response["answer"]
    assert response["links"][0]["url"] == "/payments"
