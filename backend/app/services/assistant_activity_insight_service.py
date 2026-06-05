from __future__ import annotations

from datetime import date, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

INACTIVE_PARTICIPANT_STATUSES = {"removed", "cancelled", "excluded", "deleted", "inactive"}
INACTIVE_ACTIVITY_FEE_STATUSES = {"cancelled", "excluded"}


def _money(value: int | float | None) -> str:
    return f"{int(value or 0):,}원"


def _period_dates(period: str | None = None) -> tuple[date | None, date | None]:
    today = date.today()
    if period == "week":
        start = today - timedelta(days=today.weekday())
        return start, start + timedelta(days=6)
    if period == "month" or period is None:
        start = date(today.year, today.month, 1)
        end = date(today.year + (1 if today.month == 12 else 0), 1 if today.month == 12 else today.month + 1, 1) - timedelta(days=1)
        return start, end
    if len(period) == 7 and period[4] == "-":
        year, month = period.split("-")
        start = date(int(year), int(month), 1)
        end = date(int(year) + (1 if int(month) == 12 else 0), 1 if int(month) == 12 else int(month) + 1, 1) - timedelta(days=1)
        return start, end
    return None, None


def activity_target(activity_id: Any) -> str:
    return f"/activities/{activity_id}"


def activity_fee_target(activity_id: Any) -> str:
    return f"/activities/{activity_id}?tab=activity-fee"


def normalize_text(value: str | None) -> str:
    return " ".join((value or "").lower().replace("?", " ").split())


def _is_unpaid(status: str | None) -> bool:
    return str(status or "") in {"unpaid", "partial", "need_check"}


def _active_participant_condition(ActivityParticipant, activity_id: UUID):
    return and_(
        ActivityParticipant.activity_report_id == activity_id,
        or_(
            ActivityParticipant.status.is_(None),
            ActivityParticipant.status.notin_(INACTIVE_PARTICIPANT_STATUSES),
        ),
    )


def find_activity_candidates(db: Session, query: str, *, limit: int = 5) -> list[dict[str, Any]]:
    from app.models import ActivityCategory, ActivityReport

    text = normalize_text(query)
    activities = list(db.scalars(
        select(ActivityReport)
        .where(ActivityReport.deleted_at.is_(None))
        .order_by(ActivityReport.activity_date.desc().nullslast(), ActivityReport.created_at.desc())
    ))
    category_ids = {a.category_id for a in activities if getattr(a, "category_id", None)}
    categories = {
        c.id: c.name
        for c in db.scalars(select(ActivityCategory).where(ActivityCategory.id.in_(category_ids)))
    } if category_ids else {}
    scored: list[tuple[int, date, Any]] = []
    tokens = [t for t in text.split() if len(t) >= 2 and t not in {"활동", "참여자", "참가자", "활동비", "증빙", "보고서"}]
    for activity in activities:
        haystacks = [
            normalize_text(getattr(activity, "title", "")),
            normalize_text(getattr(activity, "location", "")),
            normalize_text(categories.get(getattr(activity, "category_id", None), "")),
            str(getattr(activity, "activity_date", "") or ""),
        ]
        score = 0
        for token in tokens:
            score += sum(2 if token in item else 0 for item in haystacks)
        for item in haystacks:
            if item and item in text:
                score += 3
        if score > 0:
            scored.append((score, getattr(activity, "activity_date", None) or date.min, activity))
    scored.sort(key=lambda item: (-item[0], -item[1].toordinal()))
    return [
        {
            "activity_id": str(activity.id),
            "title": activity.title,
            "activity_date": activity.activity_date.isoformat() if activity.activity_date else None,
            "location": activity.location,
            "target_url": activity_target(activity.id),
        }
        for _, _date, activity in scored[:limit]
    ]


def get_activity_overview(db: Session, *, period: str | None = None) -> dict[str, Any]:
    from app.models import ActivityParticipant, ActivityReport, PaymentRecord, Receipt

    start, end = _period_dates(period)
    stmt = select(ActivityReport).where(ActivityReport.deleted_at.is_(None))
    if start:
        stmt = stmt.where(ActivityReport.activity_date >= start)
    if end:
        stmt = stmt.where(ActivityReport.activity_date <= end)
    activities = list(db.scalars(stmt.order_by(ActivityReport.activity_date.desc().nullslast())))
    items = []
    for activity in activities:
        participant_count = db.scalar(
            select(func.count()).select_from(ActivityParticipant).where(_active_participant_condition(ActivityParticipant, activity.id))
        ) or 0
        fee_records = list(db.scalars(
            select(PaymentRecord).where(
                and_(
                    PaymentRecord.payment_type == "activity_fee",
                    PaymentRecord.activity_report_id == activity.id,
                    PaymentRecord.status.notin_(INACTIVE_ACTIVITY_FEE_STATUSES),
                )
            )
        ))
        receipt_count = db.scalar(select(func.count()).select_from(Receipt).where(Receipt.activity_report_id == activity.id)) or 0
        items.append({
            "activity_id": str(activity.id),
            "title": activity.title,
            "activity_date": activity.activity_date.isoformat() if activity.activity_date else None,
            "location": activity.location,
            "participant_count": int(participant_count),
            "status": activity.status,
            "fee_required": sum(int(r.required_amount or 0) for r in fee_records),
            "fee_paid": sum(int(r.paid_amount or 0) for r in fee_records),
            "unpaid_count": sum(1 for r in fee_records if _is_unpaid(r.status)),
            "report_status": "written" if (activity.final_content or activity.generated_content) else "missing",
            "evidence_status": "linked" if receipt_count else "missing",
            "target_url": activity_target(activity.id),
        })
    return {"total_count": len(items), "items": items}


def get_activity_detail_insight(db: Session, activity_id: UUID) -> dict[str, Any]:
    overview = get_activity_overview(db)
    for item in overview["items"]:
        if item["activity_id"] == str(activity_id):
            return item
    raise ValueError("Activity not found")


def get_activity_fee_insight(db: Session, *, activity_id: UUID | None = None, period: str | None = None) -> dict[str, Any]:
    from app.models import ActivityReport, PaymentRecord

    stmt = select(PaymentRecord).where(
        and_(
            PaymentRecord.payment_type == "activity_fee",
            PaymentRecord.status.notin_(INACTIVE_ACTIVITY_FEE_STATUSES),
        )
    )
    if activity_id:
        stmt = stmt.where(PaymentRecord.activity_report_id == activity_id)
    records = list(db.scalars(stmt))
    if period and not activity_id:
        records = [r for r in records if str(r.period or "") == period]
    unpaid = [r for r in records if _is_unpaid(r.status)]
    activity_ids = {r.activity_report_id for r in records if r.activity_report_id}
    activities = {
        a.id: a
        for a in db.scalars(select(ActivityReport).where(ActivityReport.id.in_(activity_ids)))
    } if activity_ids else {}
    rows = []
    for aid in sorted(activity_ids, key=str):
        scoped = [r for r in records if r.activity_report_id == aid]
        scoped_unpaid = [r for r in scoped if _is_unpaid(r.status)]
        activity = activities.get(aid)
        rows.append({
            "activity_id": str(aid),
            "activity_title": activity.title if activity else "활동",
            "required_amount": sum(int(r.required_amount or 0) for r in scoped),
            "paid_amount": sum(int(r.paid_amount or 0) for r in scoped),
            "unpaid_count": len(scoped_unpaid),
            "due_amount": sum(max(0, int(r.required_amount or 0) - int(r.paid_amount or 0)) for r in scoped_unpaid),
            "target_url": activity_fee_target(aid),
        })
    return {
        "activity_id": str(activity_id) if activity_id else None,
        "total_records": len(records),
        "unpaid_count": len(unpaid),
        "due_amount": sum(max(0, int(r.required_amount or 0) - int(r.paid_amount or 0)) for r in unpaid),
        "activities": rows,
    }


def get_membership_fee_insight(db: Session, *, period: str | None = None) -> dict[str, Any]:
    from app.services.membership_fee_management_service import get_membership_fee_summary

    summary = get_membership_fee_summary(db, period=period)
    unpaid_count = summary.unpaid_count + summary.partial_count + summary.need_check_count
    return {
        "period": period,
        "total_count": summary.total_members,
        "unpaid_count": unpaid_count,
        "due_amount": summary.receivable_amount,
        "target_url": "/payments",
    }


def get_calendar_schedule_summary(db: Session, *, period: str | None = "week", event_type: str | None = None) -> dict[str, Any]:
    from app.services.calendar_event_service import list_calendar_events

    start, _end = _period_dates(period)
    start = start or date.today()
    data = list_calendar_events(db, year=start.year, month=start.month)
    items = data["items"]
    if event_type:
        items = [item for item in items if item["event_type"] == event_type]
    if period == "week":
        week_start, week_end = _period_dates("week")
        items = [item for item in items if week_start.isoformat() <= item["date"] <= week_end.isoformat()]
    return {"period": period, "items": items, "total_count": len(items), "target_url": "/dashboard"}


def get_budget_insight(db: Session, *, period: str | None = None) -> dict[str, Any]:
    from app.services.budget_service import get_budget_summary

    summary = get_budget_summary(db, period=period)
    return {
        "period": summary.get("period") or period,
        "total_income": summary["total_income"],
        "total_expense": summary["total_expense"],
        "net_change": summary["net_change"],
        "current_balance": summary["current_balance"],
        "target_url": "/budget",
    }


def get_document_evidence_summary(db: Session, *, activity_id: UUID | None = None) -> dict[str, Any]:
    from app.models import ActivityReport, Receipt

    stmt = select(ActivityReport).where(ActivityReport.deleted_at.is_(None))
    if activity_id:
        stmt = stmt.where(ActivityReport.id == activity_id)
    activities = list(db.scalars(stmt))
    rows = []
    for activity in activities:
        receipt_count = db.scalar(select(func.count()).select_from(Receipt).where(Receipt.activity_report_id == activity.id)) or 0
        report_missing = not (activity.final_content or activity.generated_content)
        if receipt_count == 0 or report_missing:
            rows.append({
                "activity_id": str(activity.id),
                "activity_title": activity.title,
                "missing_evidence": receipt_count == 0,
                "missing_report": report_missing,
                "evidence_url": f"/activities/{activity.id}?tab=evidence",
                "activity_url": activity_target(activity.id),
            })
    return {"total_count": len(rows), "items": rows}
