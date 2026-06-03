"""Task 27 Tests: Members must NOT be auto-created during activity participant import."""
from __future__ import annotations

import io

import pandas as pd
import pytest
from sqlalchemy.orm import Session

from app.models.activity import ActivityParticipant, ActivityReport
from app.models.member import Member
from app.services.activity_participant_import_service import (
    confirm_participant_import,
    preview_participant_import,
)
import uuid


def _make_excel(rows: list[dict]) -> bytes:
    df = pd.DataFrame(rows)
    buf = io.BytesIO()
    df.to_excel(buf, index=False)
    return buf.getvalue()


def _create_activity(db: Session) -> ActivityReport:
    r = ActivityReport(title="자동생성금지테스트", status="planned")
    db.add(r)
    db.flush()
    return r


class TestNoMemberAutoCreate:
    def test_preview_never_creates_member(self, db: Session) -> None:
        activity = _create_activity(db)
        before = db.query(Member).count()

        rows = [
            {"이름": "홍길동1", "학번": "2025000001"},
            {"이름": "홍길동2", "학번": "2025000002"},
            {"이름": "홍길동3", "학번": "2025000003"},
        ]
        excel = _make_excel(rows)
        preview_participant_import(db, excel, "test.xlsx", activity.id)

        assert db.query(Member).count() == before, "preview 단계에서 Member가 생성되면 안 됩니다"

    def test_confirm_without_create_new_member_action_does_not_create_member(self, db: Session) -> None:
        activity = _create_activity(db)
        before = db.query(Member).count()

        excel = _make_excel([{"이름": "홍길동", "학번": "2025123456"}])
        preview = preview_participant_import(db, excel, "test.xlsx", activity.id)

        # ignore 또는 mark_external 선택 → member 생성 없음
        confirm_participant_import(
            db,
            uuid.UUID(preview.action_id),
            row_overrides=[{"row_index": preview.rows[0].row_index, "selected_action": "mark_external"}],
        )

        assert db.query(Member).count() == before, "mark_external은 Member를 생성하면 안 됩니다"

    def test_confirm_default_action_for_unregistered_is_ignore(self, db: Session) -> None:
        activity = _create_activity(db)

        excel = _make_excel([{"이름": "홍길동", "학번": "2025123456"}])
        preview = preview_participant_import(db, excel, "test.xlsx", activity.id)

        row = preview.rows[0]
        assert row.match_status == "unregistered_candidate"
        # default action이 needs_user_selection이어야 하며 auto-create가 아니어야 함
        assert row.action != "create_new_member", "default action이 create_new_member이면 안 됩니다"

    def test_create_new_member_only_on_explicit_user_selection(self, db: Session) -> None:
        activity = _create_activity(db)
        before = db.query(Member).count()

        excel = _make_excel([{"이름": "홍길동", "학번": "2025123456"}])
        preview = preview_participant_import(db, excel, "test.xlsx", activity.id)

        # 사용자가 명시적으로 create_new_member 선택
        from app.services.activity_participant_import_service import confirm_participant_import
        result = confirm_participant_import(
            db,
            uuid.UUID(preview.action_id),
            row_overrides=[{"row_index": preview.rows[0].row_index, "selected_action": "create_new_member"}],
        )
        # confirm 후에만 member 생성
        assert db.query(Member).count() == before + 1
        assert result.created_members == 1
