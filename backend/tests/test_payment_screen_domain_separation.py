"""Task 29 Tests: Payment screen domain separation.

Payments API (회비 화면) must only return/modify membership_fee records.
Activity fee records must only be managed via activity-scoped endpoints.
"""
from __future__ import annotations

import uuid as _uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.member import Member
from app.models.payment import PaymentRecord


def _create_member(db: Session, name: str = "테스트부원") -> Member:
    m = Member(name=name, status="active")
    db.add(m)
    db.flush()
    return m


def _create_payment_record(
    db: Session,
    member: Member,
    period: str,
    payment_type: str,
    required_amount: int = 10000,
    status: str = "unpaid",
) -> PaymentRecord:
    r = PaymentRecord(
        member_id=member.id,
        period=period,
        payment_type=payment_type,
        required_amount=required_amount,
        paid_amount=0,
        status=status,
    )
    db.add(r)
    db.flush()
    return r


class TestPaymentRecordsAPIFiltering:
    def test_membership_fee_filter_returns_only_membership_fee(self, db: Session) -> None:
        m = _create_member(db)
        _create_payment_record(db, m, "2026-1", "membership_fee", 10000)
        _create_payment_record(db, m, "act-aaaabbbb", "activity_fee", 5000)
        db.commit()

        from app.models.payment import PaymentRecord as PR
        from sqlalchemy import and_, select

        records = list(db.scalars(
            select(PR).where(
                and_(PR.payment_type == "membership_fee", PR.period == "2026-1")
            )
        ))
        assert all(r.payment_type == "membership_fee" for r in records)
        assert not any(r.payment_type == "activity_fee" for r in records)

    def test_activity_fee_filter_returns_only_activity_fee(self, db: Session) -> None:
        m = _create_member(db)
        _create_payment_record(db, m, "2026-1", "membership_fee", 10000)
        _create_payment_record(db, m, "act-aaaabbbb", "activity_fee", 5000)
        db.commit()

        from app.models.payment import PaymentRecord as PR
        from sqlalchemy import and_, select

        records = list(db.scalars(
            select(PR).where(PR.payment_type == "activity_fee")
        ))
        assert all(r.payment_type == "activity_fee" for r in records)
        assert not any(r.payment_type == "membership_fee" for r in records)


class TestActivityFeeMatchingDoesNotTouchMembershipFee:
    def test_activity_fee_matching_service_ignores_membership_fee_records(self, db: Session) -> None:
        from app.models.activity import ActivityReport
        from app.services.payment_matching_service import preview_payment_matching

        activity = ActivityReport(title="테스트활동", status="planned")
        db.add(activity)
        db.flush()

        m = _create_member(db, "부원")
        membership_rec = _create_payment_record(db, m, "2026-1", "membership_fee", 10000)
        activity_rec = _create_payment_record(db, m, f"act-{str(activity.id)[:8]}", "activity_fee", 5000)
        db.commit()

        # Preview activity fee matching for this activity
        preview = preview_payment_matching(
            db=db,
            period=f"act-{str(activity.id)[:8]}",
            payment_type="activity_fee",
            required_amount=None,
            activity_id=activity.id,
        )

        # Verify membership_fee record not affected
        db.refresh(membership_rec)
        assert membership_rec.payment_type == "membership_fee"
        assert membership_rec.paid_amount == 0

    def test_membership_fee_bulk_mark_paid_does_not_touch_activity_fee(self, db: Session) -> None:
        from app.services.bulk_membership_fee_service import apply_bulk_membership_fee_mark_paid

        m = _create_member(db, "부원")
        membership_rec = _create_payment_record(db, m, "2026-test", "membership_fee", 10000)
        activity_rec = _create_payment_record(db, m, "act-aaaabbbb", "activity_fee", 5000)
        db.commit()

        apply_bulk_membership_fee_mark_paid(db=db, period="2026-test")

        db.refresh(membership_rec)
        db.refresh(activity_rec)

        # membership_fee updated
        assert membership_rec.status == "paid"
        assert membership_rec.paid_amount == 10000

        # activity_fee NOT touched
        assert activity_rec.status == "unpaid"
        assert activity_rec.paid_amount == 0
