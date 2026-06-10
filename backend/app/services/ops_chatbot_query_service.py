from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.services.term_service import get_current_term


ACTIVE_ACTIVITY_STATUSES = {
    "planned",
    "ongoing",
    "in_progress",
    "completed",
    "done",
    "draft",
    "generated",
    "confirmed",
}
EXCLUDED_ACTIVITY_STATUSES = {"cancelled", "canceled", "deleted", "archived"}
INACTIVE_PARTICIPANT_STATUSES = {"removed", "cancelled", "excluded", "deleted", "inactive"}
INACTIVE_PAYMENT_STATUSES = {"cancelled", "excluded"}
UNPAID_STATUSES = {"unpaid", "partial", "need_check"}


@dataclass
class ChatAnswer:
    answer: str
    intent: str
    data_sources: list[str]
    links: list[dict[str, str]]
    confidence: float = 0.92
    summary: list[dict[str, str]] | None = None
    items: list[dict[str, Any]] | None = None
    zero_reasons: list[str] | None = None
    scope: str | None = None
    context_used: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "answer": self.answer,
            "intent": self.intent,
            "data_sources": self.data_sources,
            "links": self.links,
            "confidence": self.confidence,
            "summary": self.summary or [],
            "items": self.items or [],
            "zero_reasons": self.zero_reasons or [],
            "scope": self.scope,
            "context_used": self.context_used or {},
        }


def _norm(value: str | None) -> str:
    return " ".join((value or "").strip().lower().split())


def _money(value: int | float | None) -> str:
    return f"{int(value or 0):,}원"


def _today() -> date:
    return date.today()


def _current_period() -> str:
    try:
        return get_current_term()
    except Exception:
        today = _today()
        return f"{today.year}-{'1' if today.month <= 6 else '2'}"


def _activity_url(activity_id: Any, tab: str | None = None) -> str:
    url = f"/activities/{activity_id}"
    if tab:
        return f"{url}?tab={tab}"
    return url


def _active_activity_query(include_cancelled: bool = False):
    from app.models import ActivityReport

    stmt = select(ActivityReport).where(ActivityReport.deleted_at.is_(None))
    if not include_cancelled:
        stmt = stmt.where(
            or_(
                ActivityReport.status.is_(None),
                ActivityReport.status.notin_(EXCLUDED_ACTIVITY_STATUSES),
            )
        )
    return stmt


def _active_participants(db: Session) -> list[Any]:
    from app.models import ActivityParticipant

    return list(
        db.scalars(
            select(ActivityParticipant).where(
                or_(
                    ActivityParticipant.status.is_(None),
                    ActivityParticipant.status.notin_(INACTIVE_PARTICIPANT_STATUSES),
                )
            )
        )
    )


def _activity_period_key(activity_id: Any) -> str:
    return f"act-{str(activity_id)[:8]}"


def _active_activity_fee_records(db: Session) -> list[Any]:
    from app.models import PaymentRecord

    return list(
        db.scalars(
            select(PaymentRecord).where(
                PaymentRecord.payment_type == "activity_fee",
                PaymentRecord.status.notin_(INACTIVE_PAYMENT_STATUSES),
            )
        )
    )


def _category_names(db: Session, category_ids: set[Any]) -> dict[Any, str]:
    if not category_ids:
        return {}
    from app.models import ActivityCategory

    return {
        category.id: category.name
        for category in db.scalars(select(ActivityCategory).where(ActivityCategory.id.in_(category_ids)))
    }


def _activity_photo_days_after(db: Session) -> int:
    from app.models import NotificationRule

    try:
        value = db.scalar(
            select(NotificationRule.days_after).where(
                NotificationRule.reminder_type == "activity_photo_missing",
                NotificationRule.enabled.is_(True),
                NotificationRule.deleted_at.is_(None),
            )
        )
    except Exception:
        value = None
    return 2 if value is None else int(value)


def _is_activity_photo_required(activity_date: date | None, days_after: int, today: date | None = None) -> bool:
    if activity_date is None:
        return False
    return activity_date <= (today or _today()) - timedelta(days=days_after)


def _report_status(activity: Any) -> str:
    if getattr(activity, "final_content", None) or getattr(activity, "generated_content", None):
        return "작성됨"
    status = str(getattr(activity, "status", "") or "")
    if status in {"generated", "completed", "done"}:
        return "작성됨"
    return "작성 필요"


def _status_label(status: str | None) -> str:
    return {
        "planned": "예정",
        "ongoing": "진행 중",
        "in_progress": "진행 중",
        "completed": "완료",
        "done": "완료",
        "draft": "초안",
        "generated": "생성됨",
        "confirmed": "확정",
        "cancelled": "취소",
        "canceled": "취소",
        "deleted": "삭제",
        "archived": "보관",
    }.get(str(status or ""), str(status or "상태 없음"))


def _build_activity_rows(
    activities: list[Any],
    participants: list[Any],
    fee_records: list[Any],
    receipts: list[Any],
    categories: dict[Any, str],
    *,
    photo_days_after: int = 2,
    today: date | None = None,
) -> list[dict[str, Any]]:
    participant_counts: dict[str, int] = defaultdict(int)
    for participant in participants:
        participant_counts[str(getattr(participant, "activity_report_id", ""))] += 1

    fees_by_activity: dict[str, list[Any]] = defaultdict(list)
    for record in fee_records:
        activity_id = getattr(record, "activity_report_id", None)
        period = str(getattr(record, "period", "") or "")
        for activity in activities:
            aid = str(getattr(activity, "id"))
            if activity_id and str(activity_id) == aid:
                fees_by_activity[aid].append(record)
                break
            if period == _activity_period_key(aid):
                fees_by_activity[aid].append(record)
                break

    receipt_counts: dict[str, int] = defaultdict(int)
    activity_photo_counts: dict[str, int] = defaultdict(int)
    need_check_counts: dict[str, int] = defaultdict(int)
    receipt_type_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for receipt in receipts:
        activity_id = getattr(receipt, "activity_report_id", None)
        if not activity_id:
            continue
        aid = str(activity_id)
        doc_type = str(getattr(receipt, "document_type", "") or "unknown")
        receipt_counts[aid] += 1
        receipt_type_counts[aid][doc_type] += 1
        if doc_type == "activity_photo":
            activity_photo_counts[aid] += 1
        if bool(getattr(receipt, "need_check", False)) or str(getattr(receipt, "evidence_status", "")) in {"missing", "pending", "need_check"}:
            need_check_counts[aid] += 1

    rows: list[dict[str, Any]] = []
    for activity in activities:
        aid = str(getattr(activity, "id"))
        scoped_fees = fees_by_activity[aid]
        paid_count = sum(1 for record in scoped_fees if str(getattr(record, "status", "")) == "paid")
        unpaid_records = [record for record in scoped_fees if str(getattr(record, "status", "")) in UNPAID_STATUSES]
        required_amount = sum(int(getattr(record, "required_amount", 0) or 0) for record in scoped_fees)
        paid_amount = sum(int(getattr(record, "paid_amount", 0) or 0) for record in scoped_fees)
        photo_count = activity_photo_counts[aid]
        activity_date = getattr(activity, "activity_date", None)
        photo_required = _is_activity_photo_required(activity_date, photo_days_after, today=today)
        missing_tasks: list[str] = []
        if unpaid_records:
            missing_tasks.append("활동비 미납 확인")
        if _report_status(activity) != "작성됨":
            missing_tasks.append("보고서 작성")
        if receipt_counts[aid] == 0:
            missing_tasks.append("증빙 연결")
        if photo_required and photo_count == 0:
            missing_tasks.append("활동 사진 업로드 확인")

        rows.append(
            {
                "activity_id": aid,
                "title": getattr(activity, "title", "활동"),
                "activity_date": activity_date.isoformat() if isinstance(activity_date, date) else None,
                "location": getattr(activity, "location", None),
                "status": getattr(activity, "status", None),
                "status_label": _status_label(getattr(activity, "status", None)),
                "category": categories.get(getattr(activity, "category_id", None)),
                "participant_count": participant_counts[aid],
                "activity_fee_status": f"{paid_count}/{len(scoped_fees)} 납부" if scoped_fees else "미설정",
                "activity_fee_paid_count": paid_count,
                "activity_fee_total_count": len(scoped_fees),
                "activity_fee_required_amount": required_amount,
                "activity_fee_paid_amount": paid_amount,
                "activity_fee_unpaid_count": len(unpaid_records),
                "report_status": _report_status(activity),
                "evidence_count": receipt_counts[aid],
                "evidence_need_check_count": need_check_counts[aid],
                "receipt_type_counts": dict(receipt_type_counts[aid]),
                "activity_photo_count": photo_count,
                "activity_photo_required": photo_required,
                "activity_photo_status": "업로드됨" if photo_count else ("확인 필요" if photo_required else "아직 필수 시점 전"),
                "checklist_status": "처리 필요" if missing_tasks else "완료",
                "todo_items": missing_tasks,
                "target_url": _activity_url(aid),
                "activity_fee_url": _activity_url(aid, "activity-fee"),
                "evidence_url": _activity_url(aid, "evidence"),
                "report_url": _activity_url(aid, "report"),
            }
        )
    rows.sort(key=lambda item: (item["activity_date"] or "0000-00-00", item["title"]), reverse=True)
    return rows


def get_activity_overview(db: Session, *, include_cancelled: bool = False) -> dict[str, Any]:
    from app.models import Receipt

    activities = list(db.scalars(_active_activity_query(include_cancelled=include_cancelled)))
    categories = _category_names(db, {getattr(activity, "category_id", None) for activity in activities if getattr(activity, "category_id", None)})
    rows = _build_activity_rows(
        activities,
        _active_participants(db),
        _active_activity_fee_records(db),
        list(db.scalars(select(Receipt))),
        categories,
        photo_days_after=_activity_photo_days_after(db),
    )
    return {
        "total_count": len(rows),
        "planned_or_draft_count": sum(1 for row in rows if row["status"] in {"planned", "draft", "generated", "confirmed"}),
        "completed_count": sum(1 for row in rows if row["status"] in {"completed", "done"}),
        "needs_action_count": sum(1 for row in rows if row["todo_items"]),
        "items": rows,
        "scope": "전체 DB 기준: 삭제된 활동과 취소 상태는 제외하고 planned/draft/completed 활동은 포함",
        "zero_reasons": [
            "활동 목록 API와 같은 기준으로 deleted_at이 없는 활동을 조회했습니다.",
            "기본 count에는 planned, draft, completed 상태가 포함됩니다.",
            "cancelled/deleted/archived 상태는 기본 count에서 제외됩니다.",
            "현재 검색어 또는 페이지 필터가 있다면 필터 조건 때문에 0건일 수 있습니다.",
        ] if not rows else [],
    }


def _find_activity(db: Session, *, activity_id: Any | None = None, query: str | None = None) -> Any | None:
    from app.models import ActivityReport

    if activity_id:
        try:
            found = db.get(ActivityReport, UUID(str(activity_id)))
        except (ValueError, TypeError):
            found = None
        if found is not None and getattr(found, "deleted_at", None) is None:
            return found
    text = _norm(query)
    if not text:
        return None
    activities = list(db.scalars(_active_activity_query()))
    exact = [activity for activity in activities if _norm(getattr(activity, "title", "")) and _norm(getattr(activity, "title", "")) in text]
    if exact:
        return exact[0]
    scored: list[tuple[int, Any]] = []
    tokens = [token for token in text.split() if len(token) >= 2 and token not in {"활동", "정보", "참여자", "활동비", "증빙", "사진"}]
    for activity in activities:
        haystack = " ".join(
            [
                _norm(getattr(activity, "title", "")),
                _norm(getattr(activity, "location", "")),
                str(getattr(activity, "activity_date", "") or ""),
            ]
        )
        score = sum(1 for token in tokens if token in haystack)
        if score:
            scored.append((score, activity))
    scored.sort(key=lambda item: (-item[0], getattr(item[1], "activity_date", None) or date.min), reverse=False)
    return scored[0][1] if scored else None


def get_activity_detail_summary(db: Session, *, activity_id: Any | None = None, activity_name: str | None = None) -> dict[str, Any] | None:
    activity = _find_activity(db, activity_id=activity_id, query=activity_name)
    if activity is None:
        return None
    overview = get_activity_overview(db)
    for row in overview["items"]:
        if row["activity_id"] == str(activity.id):
            return row
    return None


def get_member_overview(db: Session) -> dict[str, Any]:
    from app.models import Member

    members = list(db.scalars(select(Member)))
    executives = [member for member in members if bool(getattr(member, "is_executive", False))]
    return {
        "total_count": len(members),
        "active_count": sum(1 for member in members if str(getattr(member, "status", "")) == "active"),
        "executive_count": len(executives),
        "executives": [
            {
                "member_id": str(member.id),
                "name": member.name,
                "role": getattr(member, "role", None),
                "target_url": f"/members/{member.id}",
            }
            for member in executives[:5]
        ],
        "target_url": "/members",
    }


def get_membership_fee_overview(db: Session, term: str | None = None) -> dict[str, Any]:
    from app.models import Member, PaymentRecord

    term = term or _current_period()
    records = list(
        db.scalars(
            select(PaymentRecord).where(
                PaymentRecord.period == term,
                PaymentRecord.payment_type == "membership_fee",
                PaymentRecord.status.notin_(INACTIVE_PAYMENT_STATUSES),
            )
        )
    )
    member_ids = {record.member_id for record in records}
    members = {member.id: member for member in db.scalars(select(Member).where(Member.id.in_(member_ids)))} if member_ids else {}
    unpaid = [record for record in records if str(record.status) in UNPAID_STATUSES]
    return {
        "term": term,
        "total_count": len(records),
        "paid_count": sum(1 for record in records if str(record.status) == "paid"),
        "unpaid_count": len(unpaid),
        "exempt_count": sum(1 for record in records if str(record.status) == "exempt"),
        "due_amount": sum(max(0, int(record.required_amount or 0) - int(record.paid_amount or 0)) for record in unpaid),
        "unpaid_members": [
            {
                "member_id": str(record.member_id),
                "name": getattr(members.get(record.member_id), "name", "부원"),
                "status": record.status,
                "due_amount": max(0, int(record.required_amount or 0) - int(record.paid_amount or 0)),
                "target_url": "/payments",
            }
            for record in unpaid[:5]
        ],
        "target_url": "/payments",
    }


def get_activity_fee_overview(db: Session, activity_id: Any | None = None) -> dict[str, Any]:
    if activity_id:
        detail = get_activity_detail_summary(db, activity_id=activity_id)
        if not detail:
            return {"total_count": 0, "unpaid_count": 0, "due_amount": 0, "activities": []}
        return {
            "total_count": detail["activity_fee_total_count"],
            "paid_count": detail["activity_fee_paid_count"],
            "unpaid_count": detail["activity_fee_unpaid_count"],
            "required_amount": detail["activity_fee_required_amount"],
            "paid_amount": detail["activity_fee_paid_amount"],
            "due_amount": max(0, detail["activity_fee_required_amount"] - detail["activity_fee_paid_amount"]),
            "activities": [detail],
        }
    overview = get_activity_overview(db)
    rows = [row for row in overview["items"] if row["activity_fee_unpaid_count"] > 0]
    return {
        "total_count": sum(row["activity_fee_total_count"] for row in overview["items"]),
        "paid_count": sum(row["activity_fee_paid_count"] for row in overview["items"]),
        "unpaid_count": sum(row["activity_fee_unpaid_count"] for row in overview["items"]),
        "required_amount": sum(row["activity_fee_required_amount"] for row in overview["items"]),
        "paid_amount": sum(row["activity_fee_paid_amount"] for row in overview["items"]),
        "due_amount": sum(max(0, row["activity_fee_required_amount"] - row["activity_fee_paid_amount"]) for row in rows),
        "activities": rows,
    }


def get_budget_overview(db: Session, quarter: str | None = None) -> dict[str, Any]:
    from app.services.budget_service import get_budget_summary

    summary = get_budget_summary(db, operating_quarter=quarter)
    summary["target_url"] = "/budget"
    return summary


def get_evidence_overview(db: Session, activity_id: Any | None = None) -> dict[str, Any]:
    overview = get_activity_overview(db)
    rows = overview["items"]
    if activity_id:
        rows = [row for row in rows if row["activity_id"] == str(activity_id)]
    missing_evidence = [row for row in rows if row["evidence_count"] == 0 or row["evidence_need_check_count"] > 0]
    missing_photo = [row for row in rows if row["activity_photo_required"] and row["activity_photo_count"] == 0]
    return {
        "total_activity_count": len(rows),
        "missing_evidence_count": len(missing_evidence),
        "activity_photo_missing_count": len(missing_photo),
        "items": missing_evidence,
        "activity_photo_items": missing_photo,
        "target_url": "/receipts",
        "zero_reasons": [
            "활동일 기준 사진 업로드 기한이 지난 활동이 없습니다.",
            "모든 대상 활동에 활동 사진 또는 증빙이 이미 연결되어 있을 수 있습니다.",
            "알림 규칙의 days_after 기준 때문에 아직 대상이 아닐 수 있습니다.",
        ] if not missing_evidence and not missing_photo else [],
    }


def get_calendar_overview(db: Session, month: str | None = None) -> dict[str, Any]:
    from app.services.calendar_event_service import list_calendar_events

    today = _today()
    year = today.year
    month_num = today.month
    if month and len(month) == 7 and month[4] == "-":
        year = int(month[:4])
        month_num = int(month[5:])
    data = list_calendar_events(db, year=year, month=month_num)
    return {
        "month": f"{year:04d}-{month_num:02d}",
        "total_count": len(data.get("items", [])),
        "items": data.get("items", [])[:5],
        "target_url": "/dashboard",
    }


def get_todo_overview(db: Session) -> dict[str, Any]:
    overview = get_activity_overview(db)
    activity_items = [row for row in overview["items"] if row["todo_items"]]
    fee = get_membership_fee_overview(db)
    return {
        "total_count": len(activity_items) + fee["unpaid_count"],
        "missing_report": sum(1 for row in activity_items if "보고서 작성" in row["todo_items"]),
        "missing_evidence": sum(1 for row in activity_items if "증빙 연결" in row["todo_items"]),
        "missing_activity_photo": sum(1 for row in activity_items if "활동 사진 업로드 확인" in row["todo_items"]),
        "unpaid_fee": fee["unpaid_count"],
        "items": activity_items[:5],
        "target_url": "/dashboard",
    }


def search_entities(db: Session, query: str) -> dict[str, Any]:
    from app.models import ActivityReport, Member

    text = f"%{query}%"
    activities = list(
        db.scalars(
            _active_activity_query().where(
                or_(ActivityReport.title.ilike(text), ActivityReport.location.ilike(text))
            ).limit(5)
        )
    )
    members = list(db.scalars(select(Member).where(Member.name.ilike(text)).limit(5)))
    return {
        "activities": [{"label": activity.title, "url": _activity_url(activity.id)} for activity in activities],
        "members": [{"label": member.name, "url": f"/members/{member.id}"} for member in members],
    }


def classify_ops_chatbot_intent(message: str, context: dict[str, Any] | None = None) -> str:
    text = _norm(message)
    context = context or {}
    if not text:
        return "unknown"
    current_page = context.get("current_page") or context.get("page")
    has_activity_context = bool(context.get("current_activity_id") or context.get("activity_id") or context.get("last_activity_id"))
    if "사진" in text and "활동" in text:
        return "activity_photo_status" if has_activity_context or "이 활동" in text else "activity_photo_missing"
    if "활동비" in text:
        return "activity_fee_status"
    if "참여" in text or "참가" in text:
        return "activity_participants"
    if "보고서" in text:
        return "activity_report_status"
    if "체크리스트" in text or "처리 필요" in text or "할 일" in text:
        return "todo_summary" if not has_activity_context else "activity_checklist_status"
    if "증빙" in text or "영수증" in text or "빠진" in text or "누락" in text:
        return "evidence_missing"
    if "활동" in text and any(token in text for token in ["몇", "개", "있어", "목록", "각각", "어떤", "전체"]):
        return "activity_count" if any(token in text for token in ["몇", "개", "전체"]) else "activity_list"
    if has_activity_context and current_page == "activity_detail":
        return "activity_detail"
    if "회비" in text:
        if "미납" in text:
            return "unpaid_members"
        return "membership_fee_summary"
    if "부원" in text or "회원" in text or "임원" in text:
        return "executive_list" if "임원" in text else "member_count"
    if any(token in text for token in ["예산", "수입", "지출", "잔액", "분기"]):
        return "budget_summary"
    if "거래" in text:
        return "transaction_search"
    if "일정" in text or "오늘" in text or "이번 주" in text or "이번달" in text:
        return "calendar_month"
    return "unknown"


def _context_activity_id(context: dict[str, Any]) -> Any | None:
    return context.get("current_activity_id") or context.get("activity_id") or context.get("last_activity_id")


def _activity_item_for_chat(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": row["title"],
        "subtitle": " / ".join(filter(None, [row.get("activity_date"), row.get("location")])),
        "status": row["status_label"],
        "url": row["target_url"],
        "meta": {
            "참여자": f"{row['participant_count']}명",
            "활동비": row["activity_fee_status"],
            "증빙": f"{row['evidence_count']}건",
            "사진": row["activity_photo_status"],
        },
    }


def answer_ops_chatbot_question(db: Session, *, message: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    context = context or {}
    intent = classify_ops_chatbot_intent(message, context)
    activity_id = _context_activity_id(context)
    scope = "현재 활동 기준" if activity_id else "전체 DB 기준"

    if intent in {"activity_count", "activity_list"}:
        overview = get_activity_overview(db)
        items = [_activity_item_for_chat(row) for row in overview["items"][:5]]
        answer = f"현재 등록된 활동은 총 {overview['total_count']}개입니다."
        if overview["items"]:
            first = overview["items"][0]
            answer += f" 예: {first['title']} ({first.get('activity_date') or '날짜 없음'}, {first.get('location') or '장소 없음'}, 참여자 {first['participant_count']}명)."
        else:
            answer += " 0건인 이유를 기준과 함께 확인했습니다."
        return ChatAnswer(
            answer=answer,
            intent=intent,
            data_sources=["activity_reports", "activity_participants", "payment_records", "receipts"],
            links=[{"label": "활동 목록 보기", "url": "/activities"}] + ([{"label": "상세 보기", "url": overview["items"][0]["target_url"]}] if overview["items"] else []),
            summary=[
                {"label": "전체 활동", "value": f"{overview['total_count']}개"},
                {"label": "예정/초안", "value": f"{overview['planned_or_draft_count']}개"},
                {"label": "완료", "value": f"{overview['completed_count']}개"},
                {"label": "처리 필요", "value": f"{overview['needs_action_count']}개"},
            ],
            items=items,
            zero_reasons=overview["zero_reasons"],
            scope=overview["scope"],
            context_used=context,
        ).as_dict()

    if intent in {"activity_detail", "activity_participants", "activity_fee_status", "activity_report_status", "activity_photo_status", "activity_checklist_status"}:
        detail = get_activity_detail_summary(db, activity_id=activity_id, activity_name=message)
        if not detail:
            return ChatAnswer(
                answer="어떤 활동을 기준으로 볼지 찾지 못했습니다. 활동 상세 페이지에서 다시 묻거나 활동명을 함께 입력해 주세요.",
                intent=intent,
                data_sources=["activity_reports"],
                links=[{"label": "활동 목록 보기", "url": "/activities"}],
                confidence=0.62,
                scope=scope,
                context_used=context,
            ).as_dict()
        if intent == "activity_fee_status":
            answer = (
                f"{detail['title']} 활동비는 {detail['activity_fee_status']} 상태입니다. "
                f"필요 금액 {_money(detail['activity_fee_required_amount'])}, 납부 {_money(detail['activity_fee_paid_amount'])}, "
                f"미납/확인 필요 {detail['activity_fee_unpaid_count']}건입니다."
            )
        elif intent == "activity_photo_status":
            answer = (
                f"{detail['title']} 활동 사진 상태는 {detail['activity_photo_status']}입니다. "
                f"현재 활동 사진 증빙은 {detail['activity_photo_count']}건입니다."
            )
        elif intent == "activity_participants":
            answer = f"{detail['title']} 참여자는 {detail['participant_count']}명입니다."
        elif intent == "activity_report_status":
            answer = f"{detail['title']} 보고서 상태는 {detail['report_status']}입니다."
        elif intent == "activity_checklist_status":
            todo = ", ".join(detail["todo_items"]) if detail["todo_items"] else "없음"
            answer = f"{detail['title']} 체크리스트 상태는 {detail['checklist_status']}입니다. 처리 필요 항목: {todo}."
        else:
            answer = (
                f"{detail['title']}은 현재 {detail['status_label']} 상태입니다. "
                f"활동일 {detail.get('activity_date') or '미정'}, 장소 {detail.get('location') or '미입력'}, 참여자 {detail['participant_count']}명입니다. "
                f"활동비 {detail['activity_fee_status']}, 증빙 {detail['evidence_count']}건, 활동 사진 {detail['activity_photo_status']}입니다."
            )
        return ChatAnswer(
            answer=answer,
            intent=intent,
            data_sources=["activity_reports", "activity_participants", "payment_records", "receipts"],
            links=[
                {"label": "활동 상세", "url": detail["target_url"]},
                {"label": "활동비 탭", "url": detail["activity_fee_url"]},
                {"label": "증빙 탭", "url": detail["evidence_url"]},
            ],
            summary=[
                {"label": "참여자", "value": f"{detail['participant_count']}명"},
                {"label": "활동비", "value": detail["activity_fee_status"]},
                {"label": "증빙", "value": f"{detail['evidence_count']}건"},
                {"label": "사진", "value": detail["activity_photo_status"]},
            ],
            items=[_activity_item_for_chat(detail)],
            scope=scope,
            context_used=context,
        ).as_dict()

    if intent in {"activity_photo_missing", "evidence_missing"}:
        evidence = get_evidence_overview(db, activity_id=activity_id)
        rows = evidence["activity_photo_items"] if intent == "activity_photo_missing" else evidence["items"]
        answer = (
            f"활동 사진 누락 대상은 {len(rows)}건입니다."
            if intent == "activity_photo_missing"
            else f"증빙 확인이 필요한 활동은 {len(rows)}건입니다."
        )
        return ChatAnswer(
            answer=answer,
            intent=intent,
            data_sources=["activity_reports", "receipts", "notification_rules"],
            links=[{"label": row["title"], "url": row["evidence_url"]} for row in rows[:5]] or [{"label": "증빙 목록 보기", "url": "/receipts"}],
            summary=[
                {"label": "증빙 확인", "value": f"{evidence['missing_evidence_count']}건"},
                {"label": "사진 누락", "value": f"{evidence['activity_photo_missing_count']}건"},
            ],
            items=[_activity_item_for_chat(row) for row in rows[:5]],
            zero_reasons=evidence["zero_reasons"] if not rows else [],
            scope=scope,
            context_used=context,
        ).as_dict()

    if intent in {"member_count", "executive_list"}:
        member = get_member_overview(db)
        return ChatAnswer(
            answer=f"등록 부원은 총 {member['total_count']}명이고 활동 중인 부원은 {member['active_count']}명입니다. 임원은 {member['executive_count']}명입니다.",
            intent=intent,
            data_sources=["members"],
            links=[{"label": "부원 목록 보기", "url": "/members"}],
            summary=[
                {"label": "전체 부원", "value": f"{member['total_count']}명"},
                {"label": "활동 중", "value": f"{member['active_count']}명"},
                {"label": "임원", "value": f"{member['executive_count']}명"},
            ],
            items=[{"title": row["name"], "subtitle": row.get("role") or "임원", "url": row["target_url"]} for row in member["executives"]],
            scope="전체 DB 기준",
            context_used=context,
        ).as_dict()

    if intent in {"membership_fee_summary", "unpaid_members", "paid_members", "exempt_members"}:
        fee = get_membership_fee_overview(db, context.get("period"))
        return ChatAnswer(
            answer=f"{fee['term']} 회비는 총 {fee['total_count']}건 중 납부 {fee['paid_count']}건, 미납/확인 필요 {fee['unpaid_count']}건, 미수 {_money(fee['due_amount'])}입니다.",
            intent=intent,
            data_sources=["payment_records", "members"],
            links=[{"label": "회비 화면", "url": "/payments"}],
            summary=[
                {"label": "전체", "value": f"{fee['total_count']}건"},
                {"label": "납부", "value": f"{fee['paid_count']}건"},
                {"label": "미납", "value": f"{fee['unpaid_count']}건"},
                {"label": "미수", "value": _money(fee["due_amount"])},
            ],
            items=[{"title": row["name"], "subtitle": f"{row['status']} / {_money(row['due_amount'])}", "url": row["target_url"]} for row in fee["unpaid_members"]],
            scope=f"{fee['term']} 학기 기준",
            context_used=context,
        ).as_dict()

    if intent == "budget_summary":
        budget = get_budget_overview(db, context.get("quarter"))
        return ChatAnswer(
            answer=f"예산 기준 수입은 {_money(budget.get('total_income'))}, 지출은 {_money(budget.get('total_expense'))}, 증감은 {_money(budget.get('net_change'))}입니다.",
            intent=intent,
            data_sources=["bank_transactions", "payment_records", "receipts"],
            links=[{"label": "예산 관리", "url": "/budget"}, {"label": "거래내역", "url": "/transactions"}],
            summary=[
                {"label": "수입", "value": _money(budget.get("total_income"))},
                {"label": "지출", "value": _money(budget.get("total_expense"))},
                {"label": "증감", "value": _money(budget.get("net_change"))},
                {"label": "잔액", "value": _money(budget.get("current_balance"))},
            ],
            scope="예산 집계 기준",
            context_used=context,
        ).as_dict()

    if intent in {"calendar_month", "upcoming_events", "today_events", "week_events"}:
        calendar = get_calendar_overview(db)
        return ChatAnswer(
            answer=f"{calendar['month']} 일정은 {calendar['total_count']}건입니다.",
            intent=intent,
            data_sources=["calendar_events", "activity_reports"],
            links=[{"label": "대시보드 일정", "url": "/dashboard"}],
            summary=[{"label": "일정", "value": f"{calendar['total_count']}건"}],
            items=[{"title": row.get("title"), "subtitle": row.get("date"), "url": row.get("target_url") or "/dashboard"} for row in calendar["items"]],
            scope=f"{calendar['month']} 기준",
            context_used=context,
        ).as_dict()

    if intent == "todo_summary":
        todo = get_todo_overview(db)
        return ChatAnswer(
            answer=f"처리 필요 항목은 총 {todo['total_count']}건입니다. 보고서 {todo['missing_report']}건, 증빙 {todo['missing_evidence']}건, 활동 사진 {todo['missing_activity_photo']}건, 회비 미납 {todo['unpaid_fee']}건입니다.",
            intent=intent,
            data_sources=["activity_reports", "receipts", "payment_records"],
            links=[{"label": "대시보드", "url": "/dashboard"}, {"label": "알림 설정", "url": "/notifications"}],
            summary=[
                {"label": "처리 필요", "value": f"{todo['total_count']}건"},
                {"label": "보고서", "value": f"{todo['missing_report']}건"},
                {"label": "증빙", "value": f"{todo['missing_evidence']}건"},
                {"label": "활동 사진", "value": f"{todo['missing_activity_photo']}건"},
            ],
            items=[_activity_item_for_chat(row) for row in todo["items"]],
            scope="전체 DB 기준",
            context_used=context,
        ).as_dict()

    return ChatAnswer(
        answer="부원, 활동, 회비, 활동비, 예산, 증빙, 일정 중 어떤 상태를 볼지 조금 더 구체적으로 물어봐 주세요.",
        intent="unknown",
        data_sources=[],
        links=[
            {"label": "활동 목록", "url": "/activities"},
            {"label": "회비", "url": "/payments"},
            {"label": "예산 관리", "url": "/budget"},
        ],
        confidence=0.45,
        context_used=context,
    ).as_dict()
