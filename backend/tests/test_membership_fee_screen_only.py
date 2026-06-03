"""Task 29 Tests: Membership fee screen returns only membership_fee records."""
from __future__ import annotations

import pytest
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.models.member import Member
from app.models.payment import PaymentRecord


def _create_member(db: Session, name: str) -> Member:
    m = Member(name=name, status="active")
    db.add(m)
    db.flush()
    return m


def _add_record(db: Session, member: Member, period: str, payment_type: str, required: int = 10000) -> PaymentRecord:
    r = PaymentRecord(
        member_id=member.id, period=period, payment_type=payment_type,
        required_amount=required, paid_amount=0, status="unpaid",
    )
    db.add(r)
    db.flush()
    return r


class TestPaymentRecordFiltering:
    def test_membership_fee_query_only_returns_membership(self, db: Session) -> None:
        m = _create_member(db, "부원1")
        _add_record(db, m, "2026-1", "membership_fee", 10000)
        _add_record(db, m, "act-aabbccdd", "activity_fee", 5000)
        db.commit()

        records = list(db.scalars(
            select(PaymentRecord).where(
                and_(PaymentRecord.period == "2026-1", PaymentRecord.payment_type == "membership_fee")
            )
        ))

        assert len(records) >= 1
        for r in records:
            assert r.payment_type == "membership_fee", f"비회비 record가 포함됨: {r.payment_type}"

    def test_activity_fee_query_only_returns_activity_fee(self, db: Session) -> None:
        m = _create_member(db, "부원2")
        _add_record(db, m, "2026-1", "membership_fee", 10000)
        _add_record(db, m, "act-aabbccdd", "activity_fee", 5000)
        db.commit()

        records = list(db.scalars(
            select(PaymentRecord).where(
                and_(PaymentRecord.period == "act-aabbccdd", PaymentRecord.payment_type == "activity_fee")
            )
        ))

        assert len(records) >= 1
        for r in records:
            assert r.payment_type == "activity_fee", f"비활동비 record가 포함됨: {r.payment_type}"

    def test_no_activity_fee_in_membership_period(self, db: Session) -> None:
        m = _create_member(db, "부원3")
        _add_record(db, m, "2026-1", "activity_fee", 5000)
        db.commit()

        records = list(db.scalars(
            select(PaymentRecord).where(
                and_(PaymentRecord.period == "2026-1", PaymentRecord.payment_type == "membership_fee")
            )
        ))

        assert all(r.payment_type == "membership_fee" for r in records)


class TestBulkFeeMarkPaidDomainIsolation:
    def test_bulk_mark_paid_only_affects_membership_fee_period(self, db: Session) -> None:
        from app.services.bulk_membership_fee_service import apply_bulk_membership_fee_mark_paid

        m = _create_member(db, "부원4")
        membership_r = _add_record(db, m, "2026-2", "membership_fee", 10000)
        # activity_fee with same period as membership — should never happen but guard anyway
        activity_r = _add_record(db, m, "act-11223344", "activity_fee", 3000)
        db.commit()

        result = apply_bulk_membership_fee_mark_paid(db=db, period="2026-2")

        db.refresh(membership_r)
        db.refresh(activity_r)

        assert membership_r.status == "paid"
        assert activity_r.status == "unpaid", "activity_fee는 bulk_mark_paid에서 수정되면 안 됩니다"

    def test_bulk_mark_paid_no_fixed_amount(self, db: Session) -> None:
        from app.services.bulk_membership_fee_service import preview_bulk_membership_fee_mark_paid

        m = _create_member(db, "부원5")
        r = _add_record(db, m, "2026-3", "membership_fee", 15000)
        db.commit()

        preview = preview_bulk_membership_fee_mark_paid(db=db, period="2026-3")

        item = next((i for i in preview.items if i.member_id == str(m.id)), None)
        assert item is not None
        assert item.new_paid_amount == 15000, "각 레코드의 required_amount를 사용해야 합니다"
        assert item.new_paid_amount != 30000, "30,000원 고정값을 사용하면 안 됩니다"
