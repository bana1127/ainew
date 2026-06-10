import calendar
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import (
    ActivityCategory,
    ActivityParticipant,
    ActivityReport,
    BankTransaction,
    Member,
    Notification,
    NotificationRule,
    PaymentRecord,
    Receipt,
    ReferenceReport,
    UploadedFile,
)
from app.services.membership_fee_management_service import get_membership_fee_summary


router = APIRouter()

INACTIVE_PARTICIPANT_STATUSES = {"removed", "cancelled", "excluded", "deleted", "inactive"}
INACTIVE_ACTIVITY_FEE_STATUSES = {"cancelled", "excluded"}


def active_participant_condition() -> object:
    return or_(
        ActivityParticipant.status.is_(None),
        ActivityParticipant.status.notin_(INACTIVE_PARTICIPANT_STATUSES),
    )


def count_where(db: Session, model: type, *conditions: object) -> int:
    statement = select(func.count(model.id))
    if conditions:
        statement = statement.where(*conditions)
    return db.scalar(statement) or 0


@router.get("/summary")
def dashboard_summary(db: Session = Depends(get_db)) -> dict:
    # IDs of non-deleted activities — used to filter activity-scoped records
    active_activity_ids_subq = select(ActivityReport.id).where(ActivityReport.deleted_at.is_(None))

    # Unpaid activity fees: only from non-deleted activities, exclude cancelled records
    unpaid_activity_fee = db.scalar(
        select(func.count(PaymentRecord.id))
        .join(
            ActivityParticipant,
            and_(
                ActivityParticipant.activity_report_id == PaymentRecord.activity_report_id,
                ActivityParticipant.member_id == PaymentRecord.member_id,
            ),
        )
        .where(
            and_(
                PaymentRecord.payment_type == "activity_fee",
                PaymentRecord.status == "unpaid",
                PaymentRecord.status.notin_(INACTIVE_ACTIVITY_FEE_STATUSES),
                PaymentRecord.activity_report_id.in_(active_activity_ids_subq),
                active_participant_condition(),
            )
        )
    ) or 0

    membership_summary = get_membership_fee_summary(db, period=None)
    unpaid_membership_fee = (
        membership_summary.unpaid_count
        + membership_summary.partial_count
        + membership_summary.need_check_count
    )

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


@router.get("/calendar")
def dashboard_calendar(
    month: str = Query(default=None, description="YYYY-MM format, e.g. 2026-06"),
    db: Session = Depends(get_db),
) -> dict:
    """Return activity events for a given month.

    month defaults to the current month if omitted.
    Deleted activities are excluded.
    Each event includes needs_report and needs_evidence flags.
    """
    today = date.today()
    if month:
        try:
            year, mon = month.split("-")
            target = date(int(year), int(mon), 1)
        except (ValueError, AttributeError):
            target = date(today.year, today.month, 1)
    else:
        target = date(today.year, today.month, 1)

    _, last_day = calendar.monthrange(target.year, target.month)
    month_start = date(target.year, target.month, 1)
    month_end = date(target.year, target.month, last_day)

    activities = list(db.scalars(
        select(ActivityReport).where(
            and_(
                ActivityReport.deleted_at.is_(None),
                ActivityReport.activity_date >= month_start,
                ActivityReport.activity_date <= month_end,
            )
        ).order_by(ActivityReport.activity_date)
    ))

    # Batch-load receipt counts per activity
    receipt_counts: dict = {}
    participant_counts: dict = {}
    fee_status_map: dict = {}
    if activities:
        act_ids = [a.id for a in activities]
        receipt_rows = db.execute(
            select(Receipt.activity_report_id, func.count(Receipt.id))
            .where(Receipt.activity_report_id.in_(act_ids))
            .group_by(Receipt.activity_report_id)
        ).all()
        receipt_counts = {str(r[0]): r[1] for r in receipt_rows}

        part_rows = db.execute(
            select(ActivityParticipant.activity_report_id, func.count(ActivityParticipant.id))
            .where(
                and_(
                    ActivityParticipant.activity_report_id.in_(act_ids),
                    active_participant_condition(),
                )
            )
            .group_by(ActivityParticipant.activity_report_id)
        ).all()
        participant_counts = {str(r[0]): r[1] for r in part_rows}

        # Fee status: check if any non-cancelled unpaid records exist
        fee_rows = db.execute(
            select(PaymentRecord.activity_report_id, PaymentRecord.status)
            .join(
                ActivityParticipant,
                and_(
                    ActivityParticipant.activity_report_id == PaymentRecord.activity_report_id,
                    ActivityParticipant.member_id == PaymentRecord.member_id,
                ),
            )
            .where(
                and_(
                    PaymentRecord.activity_report_id.in_(act_ids),
                    PaymentRecord.payment_type == "activity_fee",
                    PaymentRecord.status.notin_(INACTIVE_ACTIVITY_FEE_STATUSES),
                    active_participant_condition(),
                )
            )
        ).all()
        fee_status_by_act: dict = {}
        for row in fee_rows:
            act_id_str = str(row[0])
            statuses = fee_status_by_act.setdefault(act_id_str, set())
            statuses.add(row[1])
        for act_id_str, statuses in fee_status_by_act.items():
            if "unpaid" in statuses or "partial" in statuses:
                fee_status_map[act_id_str] = "unpaid"
            elif "paid" in statuses:
                fee_status_map[act_id_str] = "paid"
            else:
                fee_status_map[act_id_str] = "none"

    events = []
    for act in activities:
        has_report = bool(act.final_content or act.generated_content)
        has_evidence = receipt_counts.get(str(act.id), 0) > 0
        act_id_str = str(act.id)
        events.append({
            "id": act_id_str,
            "type": "activity",
            "title": act.title or "(제목 없음)",
            "date": str(act.activity_date),
            "location": act.location or "",
            "status": act.status or "planned",
            "needs_report": not has_report,
            "needs_evidence": not has_evidence,
            "participant_count": participant_counts.get(act_id_str, 0),
            "fee_status": fee_status_map.get(act_id_str, "none"),
            "url": f"/activities/{act.id}",
        })

    return {
        "month": f"{target.year}-{target.month:02d}",
        "events": events,
    }


@router.get("/todo")
def dashboard_todo(db: Session = Depends(get_db)) -> dict:
    """Return actionable items for the dashboard todo list.

    Includes:
    - Unpaid membership fee count
    - Unpaid activity fee count
    - Activities without report body
    - Activities without receipts
    - Activities without HWPX generated document
    """
    active_activity_ids_subq = select(ActivityReport.id).where(ActivityReport.deleted_at.is_(None))

    membership_summary = get_membership_fee_summary(db, period=None)
    unpaid_membership_fee = (
        membership_summary.unpaid_count
        + membership_summary.partial_count
        + membership_summary.need_check_count
    )

    unpaid_activity_fee = db.scalar(
        select(func.count(PaymentRecord.id))
        .join(
            ActivityParticipant,
            and_(
                ActivityParticipant.activity_report_id == PaymentRecord.activity_report_id,
                ActivityParticipant.member_id == PaymentRecord.member_id,
            ),
        )
        .where(
            and_(
                PaymentRecord.payment_type == "activity_fee",
                PaymentRecord.status == "unpaid",
                PaymentRecord.status.notin_(INACTIVE_ACTIVITY_FEE_STATUSES),
                PaymentRecord.activity_report_id.in_(active_activity_ids_subq),
                active_participant_condition(),
            )
        )
    ) or 0

    # Activities without any report body (final_content or generated_content)
    no_report_activities = db.scalar(
        select(func.count(ActivityReport.id)).where(
            and_(
                ActivityReport.deleted_at.is_(None),
                ActivityReport.final_content.is_(None),
                ActivityReport.generated_content.is_(None),
            )
        )
    ) or 0

    # Activities without any linked receipts
    acts_with_receipts_subq = select(Receipt.activity_report_id).where(
        Receipt.activity_report_id.isnot(None)
    ).distinct()
    no_evidence_activities = db.scalar(
        select(func.count(ActivityReport.id)).where(
            and_(
                ActivityReport.deleted_at.is_(None),
                ActivityReport.id.notin_(acts_with_receipts_subq),
            )
        )
    ) or 0

    # Activities without HWPX generated document
    acts_with_hwpx_subq = select(UploadedFile.activity_report_id).where(
        and_(
            UploadedFile.activity_report_id.isnot(None),
            UploadedFile.file_ext == "hwpx",
            UploadedFile.file_role == "generated",
            UploadedFile.deleted_at.is_(None),
        )
    ).distinct()
    no_hwpx_activities = db.scalar(
        select(func.count(ActivityReport.id)).where(
            and_(
                ActivityReport.deleted_at.is_(None),
                ActivityReport.id.notin_(acts_with_hwpx_subq),
            )
        )
    ) or 0
    photo_days_after = db.scalar(
        select(NotificationRule.days_after).where(
            and_(
                NotificationRule.reminder_type == "activity_photo_missing",
                NotificationRule.deleted_at.is_(None),
            )
        )
    )
    photo_days_after = 2 if photo_days_after is None else int(photo_days_after)
    photo_cutoff = date.today() - timedelta(days=photo_days_after)
    acts_with_activity_photo_subq = select(Receipt.activity_report_id).where(
        and_(
            Receipt.activity_report_id.isnot(None),
            Receipt.document_type == "activity_photo",
        )
    ).distinct()
    no_activity_photo_activities = db.scalar(
        select(func.count(ActivityReport.id)).where(
            and_(
                ActivityReport.deleted_at.is_(None),
                ActivityReport.activity_date.isnot(None),
                ActivityReport.activity_date <= photo_cutoff,
                ActivityReport.id.notin_(acts_with_activity_photo_subq),
            )
        )
    ) or 0

    return {
        "unpaid_membership_fee": unpaid_membership_fee,
        "unpaid_activity_fee": unpaid_activity_fee,
        "no_report_activities": no_report_activities,
        "no_evidence_activities": no_evidence_activities,
        "no_activity_photo_activities": no_activity_photo_activities,
        "no_hwpx_activities": no_hwpx_activities,
    }
