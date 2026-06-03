"""Task 29 Tests: Activity-scoped fee matching."""
from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from app.models.activity import ActivityParticipant, ActivityReport
from app.models.member import Member
from app.models.payment import PaymentRecord
from app.services.payment_matching_service import preview_payment_matching, apply_payment_matching


def _create_activity(db: Session) -> ActivityReport:
    r = ActivityReport(title="테스트활동", status="planned")
    db.add(r)
    db.flush()
    return r


def _create_member(db: Session, name: str = "부원") -> Member:
    m = Member(name=name, status="active")
    db.add(m)
    db.flush()
    return m


def _create_payment_record(
    db: Session,
    member: Member,
    period: str,
    payment_type: str,
    required_amount: int,
) -> PaymentRecord:
    r = PaymentRecord(
        member_id=member.id,
        period=period,
        payment_type=payment_type,
        required_amount=required_amount,
        paid_amount=0,
        status="unpaid",
    )
    db.add(r)
    db.flush()
    return r


class TestActivityFeeScopedPreview:
    def test_preview_scoped_to_activity_period(self, db: Session) -> None:
        activity = _create_activity(db)
        member = _create_member(db)
        period = f"act-{str(activity.id)[:8]}"

        # Create records for this activity
        activity_rec = _create_payment_record(db, member, period, "activity_fee", 5000)
        # Create membership fee record that should NOT be touched
        membership_rec = _create_payment_record(db, member, "2026-1", "membership_fee", 10000)
        db.commit()

        preview = preview_payment_matching(
            db=db,
            period=period,
            payment_type="activity_fee",
            required_amount=None,
            activity_id=activity.id,
        )

        # Preview should use activity_fee payment_type
        assert preview.payment_type == "activity_fee"

        # membership_fee record not modified
        db.refresh(membership_rec)
        assert membership_rec.paid_amount == 0

    def test_preview_returns_correct_payment_type(self, db: Session) -> None:
        activity = _create_activity(db)
        period = f"act-{str(activity.id)[:8]}"

        preview = preview_payment_matching(
            db=db,
            period=period,
            payment_type="activity_fee",
            required_amount=None,
            activity_id=activity.id,
        )

        assert preview.payment_type == "activity_fee"

    def test_apply_does_not_create_membership_fee_records(self, db: Session) -> None:
        activity = _create_activity(db)
        member = _create_member(db)
        period = f"act-{str(activity.id)[:8]}"
        _create_payment_record(db, member, period, "activity_fee", 5000)
        db.commit()

        before_membership_count = db.query(PaymentRecord).filter_by(payment_type="membership_fee").count()

        apply_payment_matching(
            db=db,
            period=period,
            payment_type="activity_fee",
            required_amount=None,
            activity_id=activity.id,
        )

        after_membership_count = db.query(PaymentRecord).filter_by(payment_type="membership_fee").count()
        assert before_membership_count == after_membership_count, (
            "activity_fee 매칭이 membership_fee 레코드를 생성하면 안 됩니다"
        )


class TestMembershipFeeDoesNotTouchActivityFee:
    def test_membership_fee_matching_ignores_activity_fee_period(self, db: Session) -> None:
        activity = _create_activity(db)
        member = _create_member(db)
        activity_period = f"act-{str(activity.id)[:8]}"
        membership_period = "2026-1"

        activity_rec = _create_payment_record(db, member, activity_period, "activity_fee", 5000)
        membership_rec = _create_payment_record(db, member, membership_period, "membership_fee", 10000)
        db.commit()

        preview = preview_payment_matching(
            db=db,
            period=membership_period,
            payment_type="membership_fee",
            required_amount=None,
        )

        # activity_fee records not modified during membership_fee preview
        db.refresh(activity_rec)
        assert activity_rec.paid_amount == 0
        assert activity_rec.payment_type == "activity_fee"
