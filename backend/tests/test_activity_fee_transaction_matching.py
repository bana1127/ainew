"""Task 30 Tests: Activity fee transaction matching service."""
from __future__ import annotations

import uuid
from datetime import datetime

import pytest
from sqlalchemy.orm import Session

from app.models import BankTransaction, Member, PaymentRecord
from app.models.activity import ActivityParticipant, ActivityReport
from app.services.activity_fee_transaction_matching_service import (
    preview_activity_fee_transaction_matching,
    confirm_activity_fee_transaction_matching,
)


def _create_activity(db: Session, title: str = "테스트활동") -> ActivityReport:
    r = ActivityReport(title=title, status="planned")
    db.add(r)
    db.flush()
    return r


def _create_member(db: Session, name: str, student_id: str | None = None) -> Member:
    m = Member(name=name, student_id=student_id, status="active")
    db.add(m)
    db.flush()
    return m


def _create_fee_record(
    db: Session, member: Member, activity: ActivityReport, required_amount: int, status: str = "unpaid"
) -> PaymentRecord:
    period = f"act-{str(activity.id)[:8]}"
    r = PaymentRecord(
        member_id=member.id,
        period=period,
        payment_type="activity_fee",
        required_amount=required_amount,
        paid_amount=0,
        status=status,
        activity_report_id=activity.id,
    )
    db.add(r)
    db.flush()
    return r


def _create_transaction(
    db: Session, memo: str, deposit_amount: int, match_status: str = "unmatched"
) -> BankTransaction:
    tx = BankTransaction(
        transaction_datetime=datetime(2026, 6, 1, 12, 0),
        transaction_type="입금",
        memo=memo,
        withdraw_amount=0,
        deposit_amount=deposit_amount,
        balance=100000,
        match_status=match_status,
    )
    db.add(tx)
    db.flush()
    return tx


class TestPreviewExactAmountMatch:
    def test_exact_amount_and_name_is_auto_match_candidate(self, db: Session) -> None:
        activity = _create_activity(db)
        member = _create_member(db, "박민서")
        _create_fee_record(db, member, activity, 25000)
        _create_transaction(db, "박민서", 25000)
        db.commit()

        result = preview_activity_fee_transaction_matching(db, activity.id)

        auto_rows = [r for r in result.rows if r.match_status == "auto_match_candidate"]
        assert len(auto_rows) >= 1
        assert auto_rows[0].matched_member_name == "박민서"
        assert auto_rows[0].amount_difference == 0

    def test_amount_mismatch_not_auto_candidate(self, db: Session) -> None:
        activity = _create_activity(db)
        member = _create_member(db, "박민서")
        _create_fee_record(db, member, activity, 25000)
        _create_transaction(db, "박민서", 10000)
        db.commit()

        result = preview_activity_fee_transaction_matching(db, activity.id)

        mismatch_rows = [r for r in result.rows if r.match_status == "amount_mismatch"]
        auto_rows = [r for r in result.rows if r.match_status == "auto_match_candidate"]
        assert len(mismatch_rows) >= 1
        assert len(auto_rows) == 0

    def test_preview_does_not_modify_db(self, db: Session) -> None:
        activity = _create_activity(db)
        member = _create_member(db, "박민서")
        fee_rec = _create_fee_record(db, member, activity, 25000)
        tx = _create_transaction(db, "박민서", 25000)
        db.commit()

        preview_activity_fee_transaction_matching(db, activity.id)

        db.refresh(fee_rec)
        db.refresh(tx)
        assert fee_rec.status == "unpaid"
        assert fee_rec.paid_amount == 0
        assert tx.match_status == "unmatched"


class TestPreviewScopeIsolation:
    def test_only_this_activity_fee_records_considered(self, db: Session) -> None:
        activity1 = _create_activity(db, "활동1")
        activity2 = _create_activity(db, "활동2")
        member = _create_member(db, "홍길동")

        _create_fee_record(db, member, activity1, 20000)
        other_rec = _create_fee_record(db, member, activity2, 20000)
        _create_transaction(db, "홍길동", 20000)
        db.commit()

        result = preview_activity_fee_transaction_matching(db, activity1.id)

        # Preview should not reference activity2's record
        for row in result.rows:
            if row.payment_record_id:
                assert row.payment_record_id != str(other_rec.id)

    def test_membership_fee_records_excluded(self, db: Session) -> None:
        activity = _create_activity(db)
        member = _create_member(db, "김철수")

        # Only membership_fee record, no activity_fee
        membership_rec = PaymentRecord(
            member_id=member.id, period="2026-1",
            payment_type="membership_fee",
            required_amount=10000, paid_amount=0, status="unpaid",
        )
        db.add(membership_rec)
        _create_transaction(db, "김철수", 10000)
        db.commit()

        result = preview_activity_fee_transaction_matching(db, activity.id)

        for row in result.rows:
            assert row.payment_record_id != str(membership_rec.id)

    def test_already_paid_record_shown_as_already_paid(self, db: Session) -> None:
        activity = _create_activity(db)
        member = _create_member(db, "이순신")
        _create_fee_record(db, member, activity, 25000, status="paid")
        _create_transaction(db, "이순신", 25000)
        db.commit()

        result = preview_activity_fee_transaction_matching(db, activity.id)

        already_paid = [r for r in result.rows if r.match_status == "already_paid"]
        assert len(already_paid) >= 1

    def test_already_matched_transaction_shown_as_already_matched(self, db: Session) -> None:
        activity = _create_activity(db)
        member = _create_member(db, "강감찬")
        _create_fee_record(db, member, activity, 25000)
        tx = _create_transaction(db, "강감찬", 25000, match_status="matched")
        db.commit()

        result = preview_activity_fee_transaction_matching(db, activity.id)

        already = [r for r in result.rows if r.match_status == "already_matched"]
        assert len(already) >= 1


class TestConfirm:
    def test_confirm_applies_auto_match_candidates(self, db: Session) -> None:
        activity = _create_activity(db)
        member = _create_member(db, "박민서")
        fee_rec = _create_fee_record(db, member, activity, 25000)
        tx = _create_transaction(db, "박민서", 25000)
        db.commit()

        preview = preview_activity_fee_transaction_matching(db, activity.id)
        result = confirm_activity_fee_transaction_matching(db, uuid.UUID(preview.action_id))

        assert result.ok
        db.refresh(fee_rec)
        db.refresh(tx)
        assert fee_rec.status == "paid"
        assert fee_rec.paid_amount == 25000
        assert tx.match_status == "matched"

    def test_confirm_revalidates_amount(self, db: Session) -> None:
        activity = _create_activity(db)
        member = _create_member(db, "테스트")
        fee_rec = _create_fee_record(db, member, activity, 25000)
        tx = _create_transaction(db, "테스트", 25000)
        db.commit()

        preview = preview_activity_fee_transaction_matching(db, activity.id)

        # Change required_amount after preview (simulates tampering)
        fee_rec.required_amount = 30000
        db.commit()

        result = confirm_activity_fee_transaction_matching(db, uuid.UUID(preview.action_id))

        # Amount mismatch on revalidation → skipped
        db.refresh(fee_rec)
        assert fee_rec.status == "unpaid"

    def test_confirm_does_not_touch_membership_fee(self, db: Session) -> None:
        activity = _create_activity(db)
        member = _create_member(db, "박민서")
        fee_rec = _create_fee_record(db, member, activity, 25000)
        tx = _create_transaction(db, "박민서", 25000)

        membership_rec = PaymentRecord(
            member_id=member.id, period="2026-1",
            payment_type="membership_fee",
            required_amount=10000, paid_amount=0, status="unpaid",
        )
        db.add(membership_rec)
        db.commit()

        preview = preview_activity_fee_transaction_matching(db, activity.id)
        confirm_activity_fee_transaction_matching(db, uuid.UUID(preview.action_id))

        db.refresh(membership_rec)
        assert membership_rec.status == "unpaid"
        assert membership_rec.paid_amount == 0
