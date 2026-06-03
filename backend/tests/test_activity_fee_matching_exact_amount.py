"""Task 30 Tests: Activity fee matching requires exact amount."""
from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from app.models import BankTransaction, Member, PaymentRecord
from app.models.activity import ActivityReport
from app.services.activity_fee_transaction_matching_service import (
    preview_activity_fee_transaction_matching,
)


def _setup(db: Session, name: str, required: int, deposit: int):
    activity = ActivityReport(title="금액테스트", status="planned")
    db.add(activity)
    db.flush()

    member = Member(name=name, status="active")
    db.add(member)
    db.flush()

    period = f"act-{str(activity.id)[:8]}"
    fee = PaymentRecord(
        member_id=member.id, period=period, payment_type="activity_fee",
        required_amount=required, paid_amount=0, status="unpaid",
        activity_report_id=activity.id,
    )
    db.add(fee)

    from datetime import datetime
    tx = BankTransaction(
        transaction_datetime=datetime(2026, 6, 1),
        memo=name, deposit_amount=deposit,
        withdraw_amount=0, balance=100000, match_status="unmatched",
    )
    db.add(tx)
    db.commit()
    return activity, fee, tx


class TestExactAmountRequirement:
    def test_exact_amount_is_auto_match_candidate(self, db: Session) -> None:
        activity, fee, tx = _setup(db, "박민서", 25000, 25000)
        result = preview_activity_fee_transaction_matching(db, activity.id)
        auto = [r for r in result.rows if r.match_status == "auto_match_candidate"]
        assert len(auto) == 1

    def test_partial_amount_is_amount_mismatch(self, db: Session) -> None:
        activity, fee, tx = _setup(db, "박민서", 25000, 10000)
        result = preview_activity_fee_transaction_matching(db, activity.id)
        mismatch = [r for r in result.rows if r.match_status == "amount_mismatch"]
        auto = [r for r in result.rows if r.match_status == "auto_match_candidate"]
        assert len(mismatch) >= 1
        assert len(auto) == 0

    def test_overpaid_amount_is_amount_mismatch(self, db: Session) -> None:
        activity, fee, tx = _setup(db, "박민서", 25000, 30000)
        result = preview_activity_fee_transaction_matching(db, activity.id)
        mismatch = [r for r in result.rows if r.match_status == "amount_mismatch"]
        assert len(mismatch) >= 1

    def test_same_name_different_amount_not_auto(self, db: Session) -> None:
        activity = ActivityReport(title="테스트", status="planned")
        db.add(activity)
        db.flush()

        member = Member(name="이름같음", status="active")
        db.add(member)
        db.flush()

        period = f"act-{str(activity.id)[:8]}"
        fee = PaymentRecord(
            member_id=member.id, period=period, payment_type="activity_fee",
            required_amount=25000, paid_amount=0, status="unpaid",
        )
        db.add(fee)

        from datetime import datetime
        tx = BankTransaction(
            transaction_datetime=datetime(2026, 6, 1),
            memo="이름같음", deposit_amount=15000,
            withdraw_amount=0, balance=100000, match_status="unmatched",
        )
        db.add(tx)
        db.commit()

        result = preview_activity_fee_transaction_matching(db, activity.id)
        auto = [r for r in result.rows if r.match_status == "auto_match_candidate"]
        assert len(auto) == 0, "금액 다르면 이름 같아도 자동 매칭 금지"

    def test_summary_counts_correct(self, db: Session) -> None:
        activity = ActivityReport(title="요약테스트", status="planned")
        db.add(activity)
        db.flush()

        from datetime import datetime

        for i, (name, required, deposit) in enumerate([
            ("정확1", 20000, 20000),
            ("정확2", 15000, 15000),
            ("불일치1", 20000, 10000),
        ]):
            m = Member(name=name, status="active")
            db.add(m)
            db.flush()
            period = f"act-{str(activity.id)[:8]}"
            db.add(PaymentRecord(
                member_id=m.id, period=period, payment_type="activity_fee",
                required_amount=required, paid_amount=0, status="unpaid",
            ))
            db.add(BankTransaction(
                transaction_datetime=datetime(2026, 6, 1),
                memo=name, deposit_amount=deposit,
                withdraw_amount=0, balance=100000, match_status="unmatched",
            ))

        db.commit()

        result = preview_activity_fee_transaction_matching(db, activity.id)
        assert result.summary.auto_match_candidates == 2
        assert result.summary.amount_mismatch >= 1
