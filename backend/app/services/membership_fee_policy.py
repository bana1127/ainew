from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.orm import Session


DEFAULT_CURRENT_TERM = "2026-1"
DEFAULT_NEW_MEMBER_FEE = 15000
DEFAULT_EXISTING_MEMBER_FEE = 10000
DEFAULT_EXECUTIVE_FEE = 0
PAYMENT_TYPE = "membership_fee"

OFFICER_ROLE_LABELS = {
    "president": "회장",
    "vice_president": "부회장",
    "officer": "임원",
}
ROLE_TO_OFFICER_ROLE = {
    "president": "president",
    "회장": "president",
    "vice_president": "vice_president",
    "부회장": "vice_president",
    "officer": "officer",
    "임원": "officer",
    "총무": "officer",
}


@dataclass
class MembershipFeeDecision:
    member_id: UUID
    member_name: str
    student_id: str | None
    department: str | None
    joined_term: str | None
    term_code: str | None
    current_term: str
    is_officer: bool
    officer_role: str | None
    role_label: str
    fee_tier: str
    required_amount: int
    paid_amount: int
    status: str
    fee_rule_reason: str
    existing_record_id: UUID | None
    action: str


@dataclass
class MembershipFeeSummary:
    total_members: int
    current_term: str
    new_member_count: int
    existing_member_count: int
    executive_count: int
    total_required_amount: int
    total_paid_amount: int
    created_count: int
    updated_count: int
    preserved_paid_count: int


@dataclass
class MembershipFeePreview:
    period: str
    payment_type: str
    current_term: str
    new_member_fee: int
    existing_member_fee: int
    executive_fee: int
    requires_confirmation: bool
    auto_apply: bool
    action_id: str | None
    summary: MembershipFeeSummary
    rows: list[MembershipFeeDecision]


def normalize_term(raw: Any) -> str | None:
    if raw is None:
        return None
    value = str(raw).strip()
    if not value:
        return None

    normalized = value.lower()
    normalized = normalized.replace("학기", "")
    normalized = normalized.replace("년도", "년")
    normalized = normalized.replace("년", "-")
    normalized = re.sub(r"\s+", "", normalized)
    normalized = normalized.replace("_", "-").replace("/", "-")

    match = re.search(r"(\d{2,4})\D*([12])", normalized)
    if not match:
        return value

    year = int(match.group(1))
    if year < 100:
        year += 2000
    semester = match.group(2)
    return f"{year}-{semester}"


def payment_status(paid_amount: int, required_amount: int) -> str:
    if required_amount <= 0:
        return "exempt"
    if paid_amount <= 0:
        return "unpaid"
    if paid_amount < required_amount:
        return "partial"
    if paid_amount == required_amount:
        return "paid"
    return "overpaid"


def officer_role_code(member: Any) -> str | None:
    explicit = getattr(member, "officer_role", None)
    if explicit:
        return str(explicit)
    role = str(getattr(member, "role", "") or "").strip()
    mapped = ROLE_TO_OFFICER_ROLE.get(role)
    if mapped:
        return mapped
    if bool(getattr(member, "is_officer", False)) or bool(getattr(member, "is_executive", False)):
        return "officer"
    return None


def is_officer_member(member: Any) -> bool:
    return officer_role_code(member) is not None


def _term_sort_key(term: str | None) -> tuple[int, int]:
    normalized = normalize_term(term)
    if not normalized:
        return (0, 0)
    match = re.match(r"^(\d{4})-([12])$", normalized)
    if not match:
        return (0, 0)
    return (int(match.group(1)), int(match.group(2)))


def decide_membership_fee(
    member: Any,
    *,
    current_term: str,
    existing_record: Any | None = None,
    new_member_fee: int = DEFAULT_NEW_MEMBER_FEE,
    existing_member_fee: int = DEFAULT_EXISTING_MEMBER_FEE,
    executive_fee: int = DEFAULT_EXECUTIVE_FEE,
) -> MembershipFeeDecision:
    joined_term = getattr(member, "joined_term", None)
    term_code = getattr(member, "term_code", None) or normalize_term(joined_term)
    paid_amount = int(getattr(existing_record, "paid_amount", 0) or 0)
    role_code = officer_role_code(member)
    role_label = OFFICER_ROLE_LABELS.get(role_code or "", "일반 부원")

    if role_code:
        fee_tier = "executive"
        required_amount = executive_fee
        reason = f"{role_label} 직위로 임원 회비 면제"
    elif term_code == current_term:
        fee_tier = "new"
        required_amount = new_member_fee
        reason = f"가입 학기 {joined_term or term_code}가 현재 학기 {current_term}와 같아 신규 부원 회비 적용"
    elif _term_sort_key(term_code) < _term_sort_key(current_term):
        fee_tier = "existing"
        required_amount = existing_member_fee
        reason = f"가입 학기 {joined_term or term_code}가 현재 학기 {current_term}보다 이전이라 기존 부원 회비 적용"
    else:
        fee_tier = "new"
        required_amount = new_member_fee
        reason = f"가입 학기 기준 확인 필요, 기본 신규 부원 회비 적용"

    status = payment_status(paid_amount, required_amount)
    existing_id = getattr(existing_record, "id", None)
    action = "update" if existing_record is not None else "create"

    return MembershipFeeDecision(
        member_id=getattr(member, "id"),
        member_name=str(getattr(member, "name", "")),
        student_id=getattr(member, "student_id", None),
        department=getattr(member, "department", None),
        joined_term=joined_term,
        term_code=term_code,
        current_term=current_term,
        is_officer=bool(role_code),
        officer_role=role_code,
        role_label=role_label,
        fee_tier=fee_tier,
        required_amount=required_amount,
        paid_amount=paid_amount,
        status=status,
        fee_rule_reason=reason,
        existing_record_id=existing_id,
        action=action,
    )


def build_membership_fee_plan(
    members: list[Any],
    existing_records: list[Any],
    *,
    current_term: str,
    new_member_fee: int = DEFAULT_NEW_MEMBER_FEE,
    existing_member_fee: int = DEFAULT_EXISTING_MEMBER_FEE,
    executive_fee: int = DEFAULT_EXECUTIVE_FEE,
) -> tuple[list[MembershipFeeDecision], MembershipFeeSummary]:
    record_map = {
        getattr(record, "member_id"): record
        for record in existing_records
        if getattr(record, "payment_type", PAYMENT_TYPE) == PAYMENT_TYPE
    }
    rows = [
        decide_membership_fee(
            member,
            current_term=current_term,
            existing_record=record_map.get(getattr(member, "id")),
            new_member_fee=new_member_fee,
            existing_member_fee=existing_member_fee,
            executive_fee=executive_fee,
        )
        for member in members
    ]
    summary = MembershipFeeSummary(
        total_members=len(rows),
        current_term=current_term,
        new_member_count=sum(1 for row in rows if row.fee_tier == "new"),
        existing_member_count=sum(1 for row in rows if row.fee_tier == "existing"),
        executive_count=sum(1 for row in rows if row.fee_tier == "executive"),
        total_required_amount=sum(row.required_amount for row in rows),
        total_paid_amount=sum(row.paid_amount for row in rows),
        created_count=sum(1 for row in rows if row.action == "create"),
        updated_count=sum(1 for row in rows if row.action == "update"),
        preserved_paid_count=sum(1 for row in rows if row.action == "update" and row.paid_amount > 0),
    )
    return rows, summary


def resolve_current_term(db: Session, period: str | None = None) -> str:
    from app.models.setting import AppSetting

    setting = db.scalar(select(AppSetting).where(AppSetting.key == "current_term"))
    raw = None
    if setting is not None:
        value = setting.value
        if isinstance(value, dict):
            raw = value.get("term") or value.get("period") or value.get("current_term") or value.get("value")
        else:
            raw = value

    return normalize_term(raw) or normalize_term(period) or DEFAULT_CURRENT_TERM


def _active_members(db: Session) -> list[Any]:
    from app.models import Member

    return list(db.scalars(select(Member).where(Member.status == "active")))


def _existing_membership_records(db: Session, period: str) -> list[Any]:
    from app.models.payment import PaymentRecord

    return list(
        db.scalars(
            select(PaymentRecord).where(
                and_(
                    PaymentRecord.period == period,
                    PaymentRecord.payment_type == PAYMENT_TYPE,
                )
            )
        )
    )


def preview_membership_fee_generation(
    db: Session,
    *,
    period: str | None = None,
    new_member_fee: int = DEFAULT_NEW_MEMBER_FEE,
    existing_member_fee: int = DEFAULT_EXISTING_MEMBER_FEE,
    executive_fee: int = DEFAULT_EXECUTIVE_FEE,
) -> MembershipFeePreview:
    current_term = resolve_current_term(db, period)
    members = _active_members(db)
    existing_records = _existing_membership_records(db, current_term)
    rows, summary = build_membership_fee_plan(
        members,
        existing_records,
        current_term=current_term,
        new_member_fee=new_member_fee,
        existing_member_fee=existing_member_fee,
        executive_fee=executive_fee,
    )
    return MembershipFeePreview(
        period=current_term,
        payment_type=PAYMENT_TYPE,
        current_term=current_term,
        new_member_fee=new_member_fee,
        existing_member_fee=existing_member_fee,
        executive_fee=executive_fee,
        requires_confirmation=True,
        auto_apply=False,
        action_id=None,
        summary=summary,
        rows=rows,
    )


def apply_membership_fee_generation(
    db: Session,
    *,
    period: str | None = None,
    new_member_fee: int = DEFAULT_NEW_MEMBER_FEE,
    existing_member_fee: int = DEFAULT_EXISTING_MEMBER_FEE,
    executive_fee: int = DEFAULT_EXECUTIVE_FEE,
) -> dict[str, Any]:
    from app.models.payment import PaymentRecord

    preview = preview_membership_fee_generation(
        db,
        period=period,
        new_member_fee=new_member_fee,
        existing_member_fee=existing_member_fee,
        executive_fee=executive_fee,
    )
    existing_by_member = {
        row.member_id: record
        for record in _existing_membership_records(db, preview.current_term)
        for row in preview.rows
        if record.member_id == row.member_id
    }
    created = 0
    updated = 0

    for row in preview.rows:
        record = existing_by_member.get(row.member_id)
        if record is None:
            record = PaymentRecord(
                member_id=row.member_id,
                period=preview.current_term,
                payment_type=PAYMENT_TYPE,
                paid_amount=0,
            )
            db.add(record)
            created += 1
        else:
            updated += 1

        record.required_amount = row.required_amount
        record.status = payment_status(int(record.paid_amount or 0), row.required_amount)
        record.fee_tier = row.fee_tier
        record.fee_rule_reason = row.fee_rule_reason
        record.joined_term = row.joined_term
        record.current_term = preview.current_term

    db.flush()
    return {
        "period": preview.current_term,
        "payment_type": PAYMENT_TYPE,
        "created_payment_records": created,
        "updated_payment_records": updated,
        "total_members": preview.summary.total_members,
        "new_member_count": preview.summary.new_member_count,
        "existing_member_count": preview.summary.existing_member_count,
        "executive_count": preview.summary.executive_count,
        "total_required_amount": preview.summary.total_required_amount,
        "total_paid_amount": preview.summary.total_paid_amount,
        "preserved_paid_count": preview.summary.preserved_paid_count,
    }
