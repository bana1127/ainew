"""Task 27 Tests: Duplicate prevention for activity participants."""
from __future__ import annotations

import io
import uuid

import pandas as pd
import pytest
from sqlalchemy.orm import Session

from app.models.activity import ActivityParticipant, ActivityReport
from app.models.member import Member
from app.services.activity_participant_import_service import (
    confirm_participant_import,
    preview_participant_import,
)


def _make_excel(rows: list[dict]) -> bytes:
    df = pd.DataFrame(rows)
    buf = io.BytesIO()
    df.to_excel(buf, index=False)
    return buf.getvalue()


def _create_activity(db: Session) -> ActivityReport:
    r = ActivityReport(title="중복방지테스트", status="planned")
    db.add(r)
    db.flush()
    return r


def _create_member(db: Session, name: str, student_id: str | None = None) -> Member:
    m = Member(name=name, student_id=student_id, status="active")
    db.add(m)
    db.flush()
    return m


class TestSameMemberDuplicate:
    def test_same_member_same_activity_no_duplicate_on_confirm(self, db: Session) -> None:
        activity = _create_activity(db)
        member = _create_member(db, "박민서", student_id="2025170011")

        excel = _make_excel([{"이름": "박민서", "학번": "2025170011"}])
        preview = preview_participant_import(db, excel, "test.xlsx", activity.id)
        confirm_participant_import(db, uuid.UUID(preview.action_id))

        count = db.query(ActivityParticipant).filter_by(
            activity_report_id=activity.id, member_id=member.id
        ).count()
        assert count == 1

    def test_same_member_already_participant_on_second_preview(self, db: Session) -> None:
        activity = _create_activity(db)
        member = _create_member(db, "박민서", student_id="2025170011")

        excel = _make_excel([{"이름": "박민서", "학번": "2025170011"}])
        preview1 = preview_participant_import(db, excel, "test.xlsx", activity.id)
        confirm_participant_import(db, uuid.UUID(preview1.action_id))

        # 두 번째 preview
        preview2 = preview_participant_import(db, excel, "test.xlsx", activity.id)
        assert preview2.summary.already_participants == 1
        assert preview2.rows[0].participant_status == "already_participant"

    def test_second_confirm_does_not_add_participant(self, db: Session) -> None:
        activity = _create_activity(db)
        _create_member(db, "박민서", student_id="2025170011")

        excel = _make_excel([{"이름": "박민서", "학번": "2025170011"}])

        p1 = preview_participant_import(db, excel, "test.xlsx", activity.id)
        confirm_participant_import(db, uuid.UUID(p1.action_id))

        p2 = preview_participant_import(db, excel, "test.xlsx", activity.id)
        r2 = confirm_participant_import(db, uuid.UUID(p2.action_id))

        assert r2.created_participants == 0
        total = db.query(ActivityParticipant).filter_by(activity_report_id=activity.id).count()
        assert total == 1


class TestDuplicateCandidate:
    def test_duplicate_names_are_classified_correctly(self, db: Session) -> None:
        activity = _create_activity(db)
        # 동명이인
        _create_member(db, "홍길동", student_id="2025000001")
        _create_member(db, "홍길동", student_id="2025000002")

        excel = _make_excel([{"이름": "홍길동"}])
        result = preview_participant_import(db, excel, "test.xlsx", activity.id)

        assert result.summary.duplicate_candidates == 1
        row = result.rows[0]
        assert row.match_status == "duplicate_candidate"
        assert "link_existing_member" in row.available_actions

    def test_name_plus_dept_unique_match_is_matched_member(self, db: Session) -> None:
        activity = _create_activity(db)
        from app.models.member import Member as M
        m1 = M(name="홍길동", department="컴퓨터공학부", status="active")
        m2 = M(name="홍길동", department="전자공학부", status="active")
        db.add_all([m1, m2])
        db.flush()

        excel = _make_excel([{"이름": "홍길동", "학과": "컴퓨터공학부"}])
        result = preview_participant_import(db, excel, "test.xlsx", activity.id)

        # 학과 포함하면 unique 매칭
        row = result.rows[0]
        assert row.match_status == "matched_member"
        assert str(m1.id) == row.matched_member_id
