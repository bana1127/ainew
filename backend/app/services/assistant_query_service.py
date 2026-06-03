from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID


ASSISTANT_SUGGESTIONS = [
    "총 부원 몇 명이야?",
    "활동 몇 개 있어?",
    "이번 학기 회비 미납 몇 명이야?",
    "활동비 미납 있는 활동 알려줘",
    "증빙 빠진 활동 있어?",
    "이번 학기 총 수입 얼마야?",
]

QUERY_INTENTS = {
    "member_count",
    "activity_count",
    "activity_participant_count",
    "membership_fee_status",
    "activity_fee_status",
    "budget_summary",
    "cashflow_summary",
    "activity_settlement_status",
    "evidence_missing",
    "report_missing",
    "audit_readiness",
    "document_summary",
    "receipt_summary",
    "unknown",
}

MUTATION_KEYWORDS = [
    "수정",
    "삭제",
    "반영",
    "처리해",
    "처리 해",
    "완납처리",
    "완납 처리",
    "미납처리",
    "미납 처리",
    "매칭",
    "연결해",
    "연결 해",
    "분류해",
    "분류 해",
    "취소해",
    "취소 해",
    "환불해",
    "환불 해",
    "생성해",
    "생성 해",
    "등록해",
    "등록 해",
    "업데이트",
]


def current_period(today: date | None = None) -> str:
    today = today or date.today()
    half = "1" if today.month <= 6 else "2"
    return f"{today.year}-{half}"


def normalize_message(message: str) -> str:
    return " ".join((message or "").strip().split()).lower()


def is_mutation_request(message: str) -> bool:
    text = normalize_message(message)
    return any(keyword in text for keyword in MUTATION_KEYWORDS)


def route_floating_assistant_intent(
    message: str,
    context: dict[str, Any] | None = None,
) -> str:
    text = normalize_message(message)
    if not text:
        return "unknown"
    if is_mutation_request(text):
        return "unknown"
    if any(word in text for word in ["증빙", "증거", "영수증 누락"]) and any(
        word in text for word in ["빠진", "누락", "없는", "없어", "미연결"]
    ):
        return "evidence_missing"
    if "보고서" in text and any(word in text for word in ["빠진", "누락", "없는", "없어", "미작성"]):
        return "report_missing"
    if "감사" in text or "감사자료" in text:
        return "audit_readiness"
    if "활동비" in text and any(word in text for word in ["미납", "납부", "받을", "정산"]):
        return "activity_fee_status"
    if "회비" in text and any(word in text for word in ["미납", "납부", "완납", "받을"]):
        return "membership_fee_status"
    if any(word in text for word in ["참여자", "참가자", "참여했", "참석자"]):
        return "activity_participant_count"
    if "활동" in text and any(word in text for word in ["몇 개", "몇개", "총", "개 있어"]):
        return "activity_count"
    if any(word in text for word in ["흐름", "cashflow", "입출금", "입금", "출금"]):
        return "cashflow_summary"
    if any(word in text for word in ["예산", "잔액", "총 수입", "총수입", "총 지출", "총지출", "순증감"]):
        return "budget_summary"
    if "정산" in text:
        return "activity_settlement_status"
    if "영수증" in text:
        return "receipt_summary"
    if any(word in text for word in ["문서", "자료", "파일", "요약"]):
        return "document_summary"
    if any(word in text for word in ["부원", "회원", "멤버"]) and any(
        word in text for word in ["몇 명", "몇명", "총", "수"]
    ):
        return "member_count"
    if context and context.get("page") == "activity_detail" and any(word in text for word in ["몇 명", "몇명"]):
        return "activity_participant_count"
    return "unknown"


def link_for(kind: str, activity_id: Any | None = None) -> str:
    if kind == "membership_fee":
        return "/payments"
    if kind == "activity_fee":
        return f"/activities/{activity_id}?tab=activity-fee" if activity_id else "/activities"
    if kind == "evidence":
        return f"/activities/{activity_id}?tab=evidence" if activity_id else "/receipts"
    if kind == "activity":
        return f"/activities/{activity_id}" if activity_id else "/activities"
    if kind == "budget":
        return "/budget"
    if kind == "member":
        return "/members"
    if kind == "transactions":
        return "/transactions"
    if kind == "receipts":
        return "/receipts"
    return "/dashboard"


def _money(value: int | float | None) -> str:
    return f"{int(value or 0):,}원"


def _due_amount(record: Any) -> int:
    return max(0, int(getattr(record, "required_amount", 0) or 0) - int(getattr(record, "paid_amount", 0) or 0))


def _is_unpaid_status(status: str | None) -> bool:
    return str(status or "") in {"unpaid", "partial", "need_check"}


def build_chat_response(
    *,
    answer: str,
    intent: str,
    data_sources: list[str] | None = None,
    links: list[dict[str, str]] | None = None,
    confidence: float = 0.9,
) -> dict[str, Any]:
    return {
        "answer": answer,
        "intent": intent if intent in QUERY_INTENTS else "unknown",
        "data_sources": data_sources or [],
        "links": links or [],
        "confidence": confidence,
    }


def build_readonly_redirect_response(message: str) -> dict[str, Any]:
    text = normalize_message(message)
    links: list[dict[str, str]] = []
    if "활동비" in text:
        links.append({"label": "활동 목록에서 활동비 탭 열기", "url": "/activities"})
    if "회비" in text or "완납" in text or "미납" in text:
        links.append({"label": "회비 화면에서 처리", "url": "/payments"})
    if "거래" in text or "매칭" in text or "분류" in text:
        links.append({"label": "거래내역에서 preview/confirm 진행", "url": "/transactions"})
    if "증빙" in text or "영수증" in text:
        links.append({"label": "영수증 화면에서 확인", "url": "/receipts"})
    if "예산" in text:
        links.append({"label": "예산 관리에서 수정", "url": "/budget"})
    if not links:
        links.append({"label": "Assistant 작업 센터 열기", "url": "/assistant"})
    return build_chat_response(
        answer=(
            "플로팅 챗봇은 조회 전용이라 DB를 직접 수정하지 않습니다. "
            "위험 작업은 해당 화면의 preview/confirm 절차에서 진행해 주세요."
        ),
        intent="unknown",
        data_sources=[],
        links=links,
        confidence=0.99,
    )


def find_activity_from_message(db: Any, message: str) -> Any | None:
    from sqlalchemy import select

    from app.models import ActivityReport

    text = normalize_message(message)
    activities = list(db.scalars(select(ActivityReport).where(ActivityReport.deleted_at.is_(None))))
    if not activities:
        return None
    exact = [a for a in activities if normalize_message(getattr(a, "title", "")) in text]
    if exact:
        return exact[0]
    candidates: list[tuple[int, Any]] = []
    ignore = {"활동", "참여자", "참가자", "몇", "몇명", "몇", "명", "있어", "알려줘"}
    words = [w for w in text.replace("?", " ").split() if len(w) >= 2 and w not in ignore]
    for activity in activities:
        title = normalize_message(getattr(activity, "title", ""))
        score = sum(1 for word in words if word in title or title in word)
        if score:
            candidates.append((score, activity))
    if not candidates:
        return None
    candidates.sort(key=lambda item: (-item[0], getattr(item[1], "activity_date", None) or date.min))
    return candidates[0][1]


def get_member_summary(db: Any) -> dict[str, int]:
    from sqlalchemy import func, select

    from app.models import Member

    total = db.scalar(select(func.count()).select_from(Member)) or 0
    active = db.scalar(select(func.count()).select_from(Member).where(Member.status == "active")) or 0
    return {"total_members": int(total), "active_members": int(active)}


def get_activity_summary(db: Any) -> dict[str, int]:
    from sqlalchemy import func, select

    from app.models import ActivityReport

    total = db.scalar(
        select(func.count()).select_from(ActivityReport).where(ActivityReport.deleted_at.is_(None))
    ) or 0
    return {"total_activities": int(total)}


def get_activity_participant_count(db: Any, *, activity_id: UUID) -> dict[str, Any]:
    from sqlalchemy import func, select

    from app.models import ActivityParticipant, ActivityReport

    activity = db.get(ActivityReport, activity_id)
    if activity is None:
        raise ValueError("Activity not found")
    count = db.scalar(
        select(func.count())
        .select_from(ActivityParticipant)
        .where(ActivityParticipant.activity_report_id == activity_id)
    ) or 0
    return {
        "activity_id": str(activity.id),
        "activity_title": activity.title,
        "participant_count": int(count),
    }


def get_membership_fee_summary(db: Any, *, period: str | None = None) -> dict[str, Any]:
    from sqlalchemy import select

    from app.models import PaymentRecord

    period = period or current_period()
    records = list(
        db.scalars(
            select(PaymentRecord).where(
                PaymentRecord.period == period,
                PaymentRecord.payment_type == "membership_fee",
            )
        )
    )
    unpaid_records = [r for r in records if _is_unpaid_status(getattr(r, "status", None))]
    return {
        "period": period,
        "total_count": len(records),
        "unpaid_count": len(unpaid_records),
        "due_amount": sum(_due_amount(r) for r in unpaid_records),
    }


def get_activity_fee_summary(db: Any, *, period: str | None = None) -> dict[str, Any]:
    from sqlalchemy import select

    from app.models import ActivityReport, PaymentRecord

    period = period or current_period()
    records = list(
        db.scalars(
            select(PaymentRecord).where(
                PaymentRecord.period == period,
                PaymentRecord.payment_type == "activity_fee",
            )
        )
    )
    unpaid_records = [r for r in records if _is_unpaid_status(getattr(r, "status", None))]
    activity_ids = sorted({r.activity_report_id for r in unpaid_records if r.activity_report_id})
    activities = {
        activity.id: activity
        for activity in db.scalars(select(ActivityReport).where(ActivityReport.id.in_(activity_ids)))
    } if activity_ids else {}
    rows = []
    for activity_id in activity_ids:
        scoped = [r for r in unpaid_records if r.activity_report_id == activity_id]
        activity = activities.get(activity_id)
        rows.append(
            {
                "activity_id": str(activity_id),
                "activity_title": activity.title if activity else "활동",
                "unpaid_count": len(scoped),
                "due_amount": sum(_due_amount(r) for r in scoped),
                "target_url": link_for("activity_fee", activity_id),
            }
        )
    return {
        "period": period,
        "unpaid_count": len(unpaid_records),
        "due_amount": sum(_due_amount(r) for r in unpaid_records),
        "activities": rows,
    }


def get_missing_evidence_activities(db: Any) -> list[dict[str, Any]]:
    from app.services.budget_review_service import get_review_items

    items = get_review_items(db, period=current_period())
    return [
        {
            "title": item.get("title") or "증빙 누락",
            "amount": int(item.get("amount") or 0),
            "target_url": item.get("target_url") or "/receipts",
        }
        for item in items
        if item.get("type") == "missing_evidence"
    ]


def _chat_for_intent(db: Any, intent: str, message: str, context: dict[str, Any] | None) -> dict[str, Any]:
    context = context or {}
    period = context.get("period") or current_period()

    if intent == "member_count":
        summary = get_member_summary(db)
        return build_chat_response(
            answer=f"현재 등록 부원은 총 {summary['total_members']}명이고, 활동 중인 부원은 {summary['active_members']}명입니다.",
            intent=intent,
            data_sources=["members"],
            links=[{"label": "부원 화면에서 보기", "url": link_for("member")}],
        )

    if intent == "activity_count":
        summary = get_activity_summary(db)
        return build_chat_response(
            answer=f"등록된 활동은 총 {summary['total_activities']}개입니다.",
            intent=intent,
            data_sources=["activity_reports"],
            links=[{"label": "활동 목록에서 보기", "url": link_for("activity")}],
        )

    if intent == "activity_participant_count":
        raw_activity_id = context.get("activity_id")
        activity = None
        if raw_activity_id:
            activity_id = UUID(str(raw_activity_id))
        else:
            activity = find_activity_from_message(db, message)
            if activity is None:
                return build_chat_response(
                    answer="어떤 활동의 참여자 수를 볼지 활동을 먼저 선택해 주세요.",
                    intent=intent,
                    data_sources=["activity_participants"],
                    links=[{"label": "활동 목록에서 선택", "url": "/activities"}],
                    confidence=0.72,
                )
            activity_id = activity.id
        summary = get_activity_participant_count(db, activity_id=activity_id)
        return build_chat_response(
            answer=f"{summary['activity_title']} 참여자는 {summary['participant_count']}명입니다.",
            intent=intent,
            data_sources=["activity_participants", "activity_reports"],
            links=[{"label": "활동 상세에서 보기", "url": link_for("activity", summary["activity_id"])}],
        )

    if intent == "membership_fee_status":
        summary = get_membership_fee_summary(db, period=period)
        return build_chat_response(
            answer=(
                f"{summary['period']} 회비 미납/부분납/확인필요 인원은 "
                f"{summary['unpaid_count']}명이고, 받을 금액은 {_money(summary['due_amount'])}입니다."
            ),
            intent=intent,
            data_sources=["payment_records"],
            links=[{"label": "회비 화면에서 보기", "url": link_for("membership_fee")}],
        )

    if intent == "activity_fee_status":
        summary = get_activity_fee_summary(db, period=period)
        links = [
            {"label": f"{row['activity_title']} 활동비 탭", "url": row["target_url"]}
            for row in summary["activities"][:5]
        ]
        if not links:
            links = [{"label": "활동 목록에서 보기", "url": "/activities"}]
        return build_chat_response(
            answer=(
                f"{summary['period']} 활동비 미납/부분납/확인필요 기록은 "
                f"{summary['unpaid_count']}건이고, 받을 금액은 {_money(summary['due_amount'])}입니다."
            ),
            intent=intent,
            data_sources=["payment_records", "activity_reports"],
            links=links,
        )

    if intent == "budget_summary":
        from app.services.budget_service import get_budget_summary

        summary = get_budget_summary(db, period=period)
        return build_chat_response(
            answer=(
                f"{summary['period'] or period} 기준 총 수입은 {_money(summary['total_income'])}, "
                f"총 지출은 {_money(summary['total_expense'])}, "
                f"순증감은 {_money(summary['net_change'])}입니다."
            ),
            intent=intent,
            data_sources=["bank_transactions", "payment_records", "receipts"],
            links=[{"label": "예산 관리에서 보기", "url": link_for("budget")}],
        )

    if intent == "cashflow_summary":
        from app.services.budget_service import get_budget_cashflow

        rows = get_budget_cashflow(db)
        latest = rows[-1] if rows else {"bucket": "기간 없음", "income": 0, "expense": 0, "net": 0}
        return build_chat_response(
            answer=(
                f"최근 구간({latest['bucket']})의 수입은 {_money(latest['income'])}, "
                f"지출은 {_money(latest['expense'])}, 순증감은 {_money(latest['net'])}입니다."
            ),
            intent=intent,
            data_sources=["bank_transactions"],
            links=[{"label": "예산 관리에서 보기", "url": link_for("budget")}],
        )

    if intent == "activity_settlement_status":
        from app.services.budget_service import get_activity_settlements

        settlements = get_activity_settlements(db)
        need_check = [row for row in settlements if row.get("evidence_status") != "ok" or row.get("balance_amount", 0) < 0]
        return build_chat_response(
            answer=f"활동별 정산 {len(settlements)}건 중 확인이 필요한 항목은 {len(need_check)}건입니다.",
            intent=intent,
            data_sources=["activity_reports", "payment_records", "receipts"],
            links=[{"label": "예산 관리에서 활동별 정산 보기", "url": "/budget"}],
        )

    if intent == "evidence_missing":
        missing = get_missing_evidence_activities(db)
        links = [
            {"label": item["title"], "url": item["target_url"]}
            for item in missing[:5]
        ] or [{"label": "영수증 화면에서 보기", "url": link_for("receipts")}]
        return build_chat_response(
            answer=f"증빙 확인이 필요한 항목은 {len(missing)}건입니다.",
            intent=intent,
            data_sources=["receipts", "bank_transactions"],
            links=links,
        )

    if intent == "report_missing":
        from sqlalchemy import func, select

        from app.models import ActivityReport

        count = db.scalar(
            select(func.count()).select_from(ActivityReport).where(
                ActivityReport.deleted_at.is_(None),
                ActivityReport.status.in_(["draft", "missing", "need_report"]),
            )
        ) or 0
        return build_chat_response(
            answer=f"보고서 작성 또는 확인이 필요한 활동은 {int(count)}건입니다.",
            intent=intent,
            data_sources=["activity_reports"],
            links=[{"label": "활동 목록에서 보기", "url": "/activities"}],
        )

    if intent == "audit_readiness":
        from app.services.budget_review_service import get_review_items

        items = get_review_items(db, period=period)
        return build_chat_response(
            answer=f"감사자료 준비 관점에서 처리 필요 항목은 {len(items)}건입니다.",
            intent=intent,
            data_sources=["payment_records", "bank_transactions", "receipts", "budget_plans"],
            links=[{"label": "예산 관리에서 처리 항목 보기", "url": "/budget"}],
        )

    if intent in {"document_summary", "receipt_summary"}:
        from app.services.assistant_rag_service import search_assistant_documents

        results = search_assistant_documents(db, message)
        if not results:
            fallback = "/receipts" if intent == "receipt_summary" else "/references"
            return build_chat_response(
                answer="관련 문서 검색 결과를 찾지 못했습니다. 질문에 활동명, 파일명, 상점명 같은 단서를 더 넣어 주세요.",
                intent=intent,
                data_sources=["activity_reports", "receipts", "uploaded_files"],
                links=[{"label": "자료 화면에서 직접 찾기", "url": fallback}],
                confidence=0.58,
            )
        first = results[0]
        return build_chat_response(
            answer=f"가장 관련 있는 자료는 '{first['title']}'입니다. 핵심 내용: {first['snippet']}",
            intent=intent,
            data_sources=["activity_reports", "receipts", "uploaded_files", "assistant_action_proposals"],
            links=[{"label": item["title"], "url": item["target_url"]} for item in results[:4]],
            confidence=0.76,
        )

    return build_chat_response(
        answer="질문을 조금 더 구체적으로 적어 주세요. 부원 수, 활동 수, 회비 미납, 활동비 미납, 예산, 증빙 상태를 바로 확인할 수 있습니다.",
        intent="unknown",
        data_sources=[],
        links=[
            {"label": "예산 관리", "url": "/budget"},
            {"label": "회비", "url": "/payments"},
            {"label": "활동", "url": "/activities"},
        ],
        confidence=0.45,
    )


def answer_floating_assistant_chat(
    db: Any,
    *,
    message: str,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if is_mutation_request(message):
        return build_readonly_redirect_response(message)
    intent = route_floating_assistant_intent(message, context)
    return _chat_for_intent(db, intent, message, context)
