"""Task 27 Tests: Activity Participant Import Confirm."""
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
    r = ActivityReport(title="테스트활동", status="planned")
    db.add(r)
    db.flush()
    return r


def _create_member(db: Session, name: str, student_id: str | None = None, phone: str | None = None) -> Member:
    m = Member(name=name, student_id=student_id, phone=phone, status="active")
    db.add(m)
    db.flush()
    return m


class TestConfirmLinkedMember:
    def test_confirm_creates_participant(self, db: Session) -> None:
        activity = _create_activity(db)
        member = _create_member(db, "박민서", student_id="2025170011")

        excel = _make_excel([{"이름": "박민서", "학번": "2025170011"}])
        preview = preview_participant_import(db, excel, "test.xlsx", activity.id)

        result = confirm_participant_import(db, uuid.UUID(preview.action_id))

        assert result.ok is True
        assert result.created_participants == 1

        p = db.query(ActivityParticipant).filter_by(activity_report_id=activity.id, member_id=member.id).first()
        assert p is not None

    def test_confirm_members_count_unchanged(self, db: Session) -> None:
        activity = _create_activity(db)
        _create_member(db, "박민서", student_id="2025170011")
        before = db.query(Member).count()

        excel = _make_excel([{"이름": "박민서", "학번": "2025170011"}])
        preview = preview_participant_import(db, excel, "test.xlsx", activity.id)
        confirm_participant_import(db, uuid.UUID(preview.action_id))

        assert db.query(Member).count() == before


class TestConfirmExternalParticipant:
    def test_confirm_external_no_member_created(self, db: Session) -> None:
        activity = _create_activity(db)
        before = db.query(Member).count()

        excel = _make_excel([{"이름": "홍길동", "학번": "2025123456"}])
        preview = preview_participant_import(db, excel, "test.xlsx", activity.id)

        # 미등록 후보를 외부인으로 선택
        result = confirm_participant_import(
            db,
            uuid.UUID(preview.action_id),
            row_overrides=[{"row_index": preview.rows[0].row_index, "selected_action": "mark_external"}],
        )

        assert db.query(Member).count() == before
        assert result.external_participants == 1

        ext = db.query(ActivityParticipant).filter_by(
            activity_report_id=activity.id, member_id=None
        ).first()
        assert ext is not None
        assert ext.external_name == "홍길동"

    def test_confirm_ignore_no_participant_created(self, db: Session) -> None:
        activity = _create_activity(db)

        excel = _make_excel([{"이름": "홍길동", "학번": "2025123456"}])
        preview = preview_participant_import(db, excel, "test.xlsx", activity.id)

        result = confirm_participant_import(
            db,
            uuid.UUID(preview.action_id),
            row_overrides=[{"row_index": preview.rows[0].row_index, "selected_action": "ignore"}],
        )

        assert result.ignored_rows == 1
        assert db.query(ActivityParticipant).filter_by(activity_report_id=activity.id).count() == 0


class TestConfirmCreateNewMember:
    def test_create_new_member_on_confirm(self, db: Session) -> None:
        activity = _create_activity(db)
        before = db.query(Member).count()

        excel = _make_excel([{"이름": "홍길동", "학번": "2025123456"}])
        preview = preview_participant_import(db, excel, "test.xlsx", activity.id)

        # preview 단계에서는 member 생성 없음
        assert db.query(Member).count() == before

        result = confirm_participant_import(
            db,
            uuid.UUID(preview.action_id),
            row_overrides=[{"row_index": preview.rows[0].row_index, "selected_action": "create_new_member"}],
        )

        # confirm 후에만 member 생성
        assert result.created_members == 1
        assert db.query(Member).count() == before + 1


class TestDuplicatePrevention:
    def test_same_file_reimport_no_duplicate(self, db: Session) -> None:
        activity = _create_activity(db)
        member = _create_member(db, "박민서", student_id="2025170011")
        excel = _make_excel([{"이름": "박민서", "학번": "2025170011"}])

        # 첫 번째 import
        preview1 = preview_participant_import(db, excel, "test.xlsx", activity.id)
        confirm_participant_import(db, uuid.UUID(preview1.action_id))
        assert db.query(ActivityParticipant).filter_by(activity_report_id=activity.id).count() == 1

        # 두 번째 import - 중복 생성 금지
        preview2 = preview_participant_import(db, excel, "test.xlsx", activity.id)
        result2 = confirm_participant_import(db, uuid.UUID(preview2.action_id))
        assert db.query(ActivityParticipant).filter_by(activity_report_id=activity.id).count() == 1
        assert result2.created_participants == 0

    def test_same_external_reimport_no_duplicate(self, db: Session) -> None:
        activity = _create_activity(db)
        excel = _make_excel([{"이름": "홍길동", "학번": "2025123456"}])

        # 첫 번째 import
        preview1 = preview_participant_import(db, excel, "test.xlsx", activity.id)
        confirm_participant_import(
            db,
            uuid.UUID(preview1.action_id),
            row_overrides=[{"row_index": preview1.rows[0].row_index, "selected_action": "mark_external"}],
        )
        ext_count_1 = db.query(ActivityParticipant).filter_by(activity_report_id=activity.id, member_id=None).count()
        assert ext_count_1 == 1

        # 두 번째 import
        preview2 = preview_participant_import(db, excel, "test.xlsx", activity.id)
        confirm_participant_import(
            db,
            uuid.UUID(preview2.action_id),
            row_overrides=[{"row_index": preview2.rows[0].row_index, "selected_action": "mark_external"}],
        )
        ext_count_2 = db.query(ActivityParticipant).filter_by(activity_report_id=activity.id, member_id=None).count()
        # 중복 생성 금지
        assert ext_count_2 == ext_count_1
