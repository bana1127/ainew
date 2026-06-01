from fastapi import APIRouter, Depends
from sqlalchemy import func, or_, select
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
def dashboard_summary(db: Session = Depends(get_db)) -> dict[str, int]:
    return {
        "total_members": count_where(db, Member),
        "active_members": count_where(db, Member, Member.status == "active"),
        "total_activity_categories": count_where(db, ActivityCategory),
        "total_reference_reports": count_where(db, ReferenceReport),
        "total_activity_reports": count_where(db, ActivityReport),
        "draft_reports": count_where(db, ActivityReport, ActivityReport.status == "draft"),
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
        "total_deposit_amount": db.scalar(select(func.coalesce(func.sum(BankTransaction.deposit_amount), 0))) or 0,
        "total_withdraw_amount": db.scalar(select(func.coalesce(func.sum(BankTransaction.withdraw_amount), 0))) or 0,
        "total_payment_records": count_where(db, PaymentRecord),
        "unpaid_count": count_where(db, PaymentRecord, PaymentRecord.status == "unpaid"),
        "unread_notifications": count_where(db, Notification, Notification.is_read.is_(False)),
    }

