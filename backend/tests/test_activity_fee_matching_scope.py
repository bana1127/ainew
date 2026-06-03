"""Task 30 Tests: Activity fee matching scope isolation."""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from app.models import BankTransaction, Member, PaymentRecord
from app.models.activity import ActivityReport
from app.services.activity_fee_transaction_matching_service import (
    confirm_activity_fee_transaction_matching,
    preview_activity_fee_transaction_matching,
)


def _make(db: Session, name: str, activity: ActivityReport, required: int, tx_amount: int):
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
        memo=name, deposit_amount=tx_amount,
        withdraw_amount=0, balance=100000, match_status="unmatched",
    )
    db.add(tx)
    db.flush()
    return member, fee, tx


class TestScopeIsolation:
    def test_other_activity_fee_not_modified(self, db: Session) -> None:
        act1 = ActivityReport(title="활동A", status="planned")
        act2 = ActivityReport(title="활동B", status="planned")
        db.add_all([act1, act2])
        db.flush()

        _, fee1, _ = _make(db, "김철수", act1, 20000, 20000)
        _, fee2, _ = _make(db, "이영희", act2, 20000, 20000)
        db.commit()

        preview = preview_activity_fee_transaction_matching(db, act1.id)
        confirm_activity_fee_transaction_matching(db, uuid.UUID(preview.action_id))

        db.refresh(fee1)
        db.refresh(fee2)

        assert fee1.status == "paid", "activity1 fee should be paid"
        assert fee2.status == "unpaid", "activity2 fee must NOT be modified"

    def test_membership_fee_not_touched(self, db: Session) -> None:
        activity = ActivityReport(title="테스트", status="planned")
        db.add(activity)
        db.flush()

        member = Member(name="박지성", status="active")
        db.add(member)
        db.flush()

        period = f"act-{str(activity.id)[:8]}"
        fee = PaymentRecord(
            member_id=member.id, period=period, payment_type="activity_fee",
            required_amount=15000, paid_amount=0, status="unpaid",
            activity_report_id=activity.id,
        )
        membership = PaymentRecord(
            member_id=member.id, period="2026-1", payment_type="membership_fee",
            required_amount=10000, paid_amount=0, status="unpaid",
        )
        db.add_all([fee, membership])

        from datetime import datetime
        tx = BankTransaction(
            transaction_datetime=datetime(2026, 6, 1),
            memo="박지성", deposit_amount=15000,
            withdraw_amount=0, balance=100000, match_status="unmatched",
        )
        db.add(tx)
        db.commit()

        preview = preview_activity_fee_transaction_matching(db, activity.id)
        confirm_activity_fee_transaction_matching(db, uuid.UUID(preview.action_id))

        db.refresh(fee)
        db.refresh(membership)

        assert fee.status == "paid"
        assert membership.status == "unpaid", "membership_fee 절대 수정 금지"

    def test_action_proposal_scoped_to_activity(self, db: Session) -> None:
        activity = ActivityReport(title="범위테스트", status="planned")
        db.add(activity)
        db.flush()
        db.commit()

        preview = preview_activity_fee_transaction_matching(db, activity.id)

        from app.models.assistant_action import AssistantActionProposal
        proposal = db.get(AssistantActionProposal, uuid.UUID(preview.action_id))
        assert proposal is not None
        assert str(proposal.activity_id) == str(activity.id)
        assert proposal.action_type == "activity_fee_transaction_match"
