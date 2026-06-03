"""Task 28 Tests: Bulk membership fee mark paid service."""
from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from app.models.member import Member
from app.models.payment import PaymentRecord
from app.services.bulk_membership_fee_service import (
    apply_bulk_membership_fee_mark_paid,
    preview_bulk_membership_fee_mark_paid,
)


def _create_member(db: Session, name: str, is_executive: bool = False) -> Member:
    m = Member(name=name, status="active", is_executive=is_executive)
    db.add(m)
    db.flush()
    return m


def _create_payment_record(db: Session, member: Member, period: str, required_amount: int, payment_type: str = "membership_fee") -> PaymentRecord:
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


class TestBulkPreview:
    def test_preview_uses_each_record_amount(self, db: Session) -> None:
        m1 = _create_member(db, "신규부원")
        m2 = _create_member(db, "기존부원")
        r1 = _create_payment_record(db, m1, "2026-1", 15000)
        r2 = _create_payment_record(db, m2, "2026-1", 10000)

        preview = preview_bulk_membership_fee_mark_paid(db, "2026-1")

        items_by_member = {item.member_id: item for item in preview.items}
        assert items_by_member[str(m1.id)].new_paid_amount == 15000
        assert items_by_member[str(m2.id)].new_paid_amount == 10000

    def test_preview_never_uses_30000_fixed(self, db: Session) -> None:
        m = _create_member(db, "테스트부원")
        _create_payment_record(db, m, "2026-1", 10000)

        preview = preview_bulk_membership_fee_mark_paid(db, "2026-1")

        for item in preview.items:
            assert item.new_paid_amount != 30000, "30,000원 고정 금액을 사용하면 안 됩니다"
            assert item.required_amount == item.new_paid_amount

    def test_executive_required_zero_becomes_exempt(self, db: Session) -> None:
        exec_m = _create_member(db, "임원", is_executive=True)
        _create_payment_record(db, exec_m, "2026-1", 0)

        preview = preview_bulk_membership_fee_mark_paid(db, "2026-1")

        item = next(i for i in preview.items if i.member_id == str(exec_m.id))
        assert item.new_status == "exempt"

    def test_preview_does_not_touch_activity_fee(self, db: Session) -> None:
        m = _create_member(db, "부원")
        _create_payment_record(db, m, "2026-1", 10000, payment_type="membership_fee")
        activity_rec = _create_payment_record(db, m, "2026-1", 5000, payment_type="activity_fee")

        preview = preview_bulk_membership_fee_mark_paid(db, "2026-1")

        # preview items should only contain membership_fee
        for item in preview.items:
            rec = db.get(PaymentRecord, item.payment_record_id)
            assert rec is None or rec.payment_type == "membership_fee"

    def test_preview_db_unchanged(self, db: Session) -> None:
        m = _create_member(db, "부원")
        r = _create_payment_record(db, m, "2026-1", 10000)

        preview_bulk_membership_fee_mark_paid(db, "2026-1")

        r_fresh = db.get(PaymentRecord, r.id)
        assert r_fresh.paid_amount == 0
        assert r_fresh.status == "unpaid"


class TestBulkApply:
    def test_apply_sets_paid_amount_to_required(self, db: Session) -> None:
        m = _create_member(db, "부원")
        r = _create_payment_record(db, m, "2026-1", 10000)

        result = apply_bulk_membership_fee_mark_paid(db, "2026-1")

        assert result.ok is True
        assert result.updated_count == 1

        r_fresh = db.get(PaymentRecord, r.id)
        assert r_fresh.paid_amount == 10000
        assert r_fresh.status == "paid"

    def test_apply_different_amounts_per_member(self, db: Session) -> None:
        m1 = _create_member(db, "신규")
        m2 = _create_member(db, "기존")
        r1 = _create_payment_record(db, m1, "2026-1", 15000)
        r2 = _create_payment_record(db, m2, "2026-1", 10000)

        apply_bulk_membership_fee_mark_paid(db, "2026-1")

        assert db.get(PaymentRecord, r1.id).paid_amount == 15000
        assert db.get(PaymentRecord, r2.id).paid_amount == 10000

    def test_apply_does_not_touch_activity_fee(self, db: Session) -> None:
        m = _create_member(db, "부원")
        _create_payment_record(db, m, "2026-1", 10000, payment_type="membership_fee")
        act_r = _create_payment_record(db, m, "2026-1", 5000, payment_type="activity_fee")

        apply_bulk_membership_fee_mark_paid(db, "2026-1")

        act_fresh = db.get(PaymentRecord, act_r.id)
        assert act_fresh.paid_amount == 0, "activity_fee는 수정되면 안 됩니다"
        assert act_fresh.status == "unpaid"

    def test_apply_idempotent(self, db: Session) -> None:
        m = _create_member(db, "부원")
        r = _create_payment_record(db, m, "2026-1", 10000)

        apply_bulk_membership_fee_mark_paid(db, "2026-1")
        result2 = apply_bulk_membership_fee_mark_paid(db, "2026-1")

        assert result2.skipped_count == 1
        assert db.get(PaymentRecord, r.id).paid_amount == 10000
