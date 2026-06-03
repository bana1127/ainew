from fastapi import APIRouter, Depends
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import (
    ActivityCategory,
    ActivityReport,
    BankTransaction,
    Member,
    Notification,
    PaymentRecord,
    Receipt,
    ReferenceReport,
)


router = APIRouter()


def count_where(db: Session, model: type, *conditions: object) -> int:
    statement = select(func.count(model.id))
    if conditions:
        statement = statement.where(*conditions)
    return db.scalar(statement) or 0


@router.get("/summary")
def dashboard_summary(db: Session = Depends(get_db)) -> dict:
    # IDs of non-deleted activities — used to filter activity-scoped records
    active_activity_ids_subq = select(ActivityReport.id).where(ActivityReport.deleted_at.is_(None))

    # Unpaid activity fees: only from non-deleted activities
    unpaid_activity_fee = db.scalar(
        select(func.count(PaymentRecord.id)).where(
            and_(
                PaymentRecord.payment_type == "activity_fee",
                PaymentRecord.status == "unpaid",
                or_(
                    PaymentRecord.activity_report_id.is_(None),
                    PaymentRecord.activity_report_id.in_(active_activity_ids_subq),
                ),
            )
        )
    ) or 0

    # Unpaid membership fees — includes partial and need_check alongside unpaid
    unpaid_membership_fee = db.scalar(
        select(func.count(PaymentRecord.id)).where(
            and_(
                PaymentRecord.payment_type == "membership_fee",
                PaymentRecord.status.in_(["unpaid", "partial", "need_check"]),
            )
        )
    ) or 0

    return {
        "total_members": count_where(db, Member),
        "active_members": count_where(db, Member, Member.status == "active"),
        "total_activity_categories": count_where(db, ActivityCategory),
        "total_reference_reports": count_where(db, ReferenceReport),
        # Only count non-deleted activities
        "total_activity_reports": count_where(
            db, ActivityReport, ActivityReport.deleted_at.is_(None)
        ),
        "draft_reports": count_where(
            db, ActivityReport,
            ActivityReport.deleted_at.is_(None),
            ActivityReport.status == "draft",
        ),
        "total_receipts": count_where(db, Receipt),
        "pending_receipts": count_where(
            db,
            Receipt,
            or_(
                Receipt.evidence_status.in_(["pending", "need_check", "invalid"]),
                Receipt.need_check.is_(True),
            ),
        ),
        "total_transactions": count_where(db, BankTransaction),
        "total_deposit_amount": db.scalar(
            select(func.coalesce(func.sum(BankTransaction.deposit_amount), 0))
        ) or 0,
        "total_withdraw_amount": db.scalar(
            select(func.coalesce(func.sum(BankTransaction.withdraw_amount), 0))
        ) or 0,
        "total_payment_records": count_where(db, PaymentRecord),
        # unpaid_count = sum of both types (for backward compat)
        "unpaid_count": unpaid_membership_fee + unpaid_activity_fee,
        # Broken-out counts for richer UI
        "unpaid_membership_fee_count": unpaid_membership_fee,
        "unpaid_activity_fee_count": unpaid_activity_fee,
        "unread_notifications": count_where(db, Notification, Notification.is_read.is_(False)),
    }

