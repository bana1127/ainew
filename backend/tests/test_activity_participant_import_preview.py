"""Task 27 Tests: Activity Participant Import Preview (DB 미반영 확인)."""
from __future__ import annotations

import io
import uuid

import pandas as pd
import pytest
from sqlalchemy.orm import Session

from app.models.activity import ActivityParticipant, ActivityReport
from app.models.member import Member
from app.services.activity_participant_import_service import (
    preview_participant_import,
)


def _make_excel(rows: list[dict]) -> bytes:
    df = pd.DataFrame(rows)
    buf = io.BytesIO()
    df.to_excel(buf, index=False)
    return buf.getvalue()


def _create_activity(db: Session, title: str = "테스트활동") -> ActivityReport:
    r = ActivityReport(title=title, status="planned")
    db.add(r)
    db.flush()
    return r


def _create_member(db: Session, name: str, student_id: str | None = None, phone: str | None = None, department: str | None = None) -> Member:
    m = Member(name=name, student_id=student_id, phone=phone, department=department, status="active")
    db.add(m)
    db.flush()
    return m


class TestPreviewMatchedMember:
    def test_matched_member_no_participant_created(self, db: Session) -> None:
        activity = _create_activity(db)
        member = _create_member(db, "박민서", student_id="2025170011")

        excel = _make_excel([{"이름": "박민서", "학번": "2025170011", "학과": "생명화학공학과"}])
        result = preview_participant_import(db, excel, "test.xlsx", activity.id)

        assert result.summary.matched_members == 1
        # DB에 ActivityParticipant가 생성되어서는 안 됨
        count = db.query(ActivityParticipant).filter_by(activity_report_id=activity.id).count()
        assert count == 0

    def test_matched_row_has_correct_status(self, db: Session) -> None:
        activity = _create_activity(db)
        _create_member(db, "박민서", student_id="2025170011")

        excel = _make_excel([{"이름": "박민서", "학번": "2025170011"}])
        result = preview_participant_import(db, excel, "test.xlsx", activity.id)

        row = result.rows[0]
        assert row.match_status == "matched_member"
        assert row.participant_status == "will_create"
        assert row.action == "link_existing_member"

    def test_members_count_unchanged_after_preview(self, db: Session) -> None:
        activity = _create_activity(db)
        _create_member(db, "박민서", student_id="2025170011")

        before = db.query(Member).count()
        excel = _make_excel([{"이름": "박민서", "학번": "2025170011"}])
        preview_participant_import(db, excel, "test.xlsx", activity.id)

        after = db.query(Member).count()
        assert before == after


class TestPreviewUnregisteredCandidate:
    def test_unregistered_no_member_created(self, db: Session) -> None:
        activity = _create_activity(db)
        before = db.query(Member).count()

        excel = _make_excel([{"이름": "홍길동", "학번": "2025123456"}])
        result = preview_participant_import(db, excel, "test.xlsx", activity.id)

        assert result.summary.unregistered_candidates == 1
        assert db.query(Member).count() == before

    def test_unregistered_no_participant_created(self, db: Session) -> None:
        activity = _create_activity(db)

        excel = _make_excel([{"이름": "홍길동", "학번": "2025123456"}])
        result = preview_participant_import(db, excel, "test.xlsx", activity.id)

        count = db.query(ActivityParticipant).filter_by(activity_report_id=activity.id).count()
        assert count == 0

    def test_unregistered_available_actions(self, db: Session) -> None:
        activity = _create_activity(db)

        excel = _make_excel([{"이름": "홍길동", "학번": "2025123456"}])
        result = preview_participant_import(db, excel, "test.xlsx", activity.id)

        row = result.rows[0]
        assert "mark_external" in row.available_actions
        assert "ignore" in row.available_actions

    def test_action_id_returned(self, db: Session) -> None:
        activity = _create_activity(db)
        excel = _make_excel([{"이름": "홍길동", "학번": "2025123456"}])
        result = preview_participant_import(db, excel, "test.xlsx", activity.id)

        assert result.action_id
        # UUID 형식이어야 함
        uuid.UUID(result.action_id)


class TestPreviewAlreadyParticipant:
    def test_already_participant_shown_correctly(self, db: Session) -> None:
        activity = _create_activity(db)
        member = _create_member(db, "박민서", student_id="2025170011")
        # 미리 참여자로 추가
        db.add(ActivityParticipant(activity_report_id=activity.id, member_id=member.id, role="participant"))
        db.flush()

        excel = _make_excel([{"이름": "박민서", "학번": "2025170011"}])
        result = preview_participant_import(db, excel, "test.xlsx", activity.id)

        assert result.summary.already_participants == 1
        assert result.rows[0].participant_status == "already_participant"

    def test_preview_does_not_duplicate_existing_participant(self, db: Session) -> None:
        activity = _create_activity(db)
        member = _create_member(db, "박민서", student_id="2025170011")
        db.add(ActivityParticipant(activity_report_id=activity.id, member_id=member.id))
        db.flush()
        count_before = db.query(ActivityParticipant).filter_by(activity_report_id=activity.id).count()

        excel = _make_excel([{"이름": "박민서", "학번": "2025170011"}])
        preview_participant_import(db, excel, "test.xlsx", activity.id)

        assert db.query(ActivityParticipant).filter_by(activity_report_id=activity.id).count() == count_before
