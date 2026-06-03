from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import ActivityParticipant, ActivityReport, Member
from app.models.payment import PaymentRecord
from app.routers.common import apply_updates, commit_or_400, get_or_404
from app.schemas import MemberCreate, MemberRead, MemberUpdate


router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic schemas (Task 26)
# ---------------------------------------------------------------------------

class MemberImportRowOut(BaseModel):
    row_index: int
    name: str | None
    student_id: str | None
    department: str | None
    phone: str | None
    email: str | None
    # Oui Parfum extended fields
    gender: str | None = None
    grade: str | None = None
    birth_year: int | None = None
    joined_term: str | None = None
    term_code: str | None = None
    is_executive: bool = False
    role: str | None = None
    is_officer: bool = False
    officer_role: str | None = None
    action: str
    matched_member_id: str | None
    diff: dict[str, Any]
    reason: str
    available_actions: list[str]


class MemberImportSummaryOut(BaseModel):
    total_rows: int
    new_members: int
    updates: int
    duplicate_candidates: int
    needs_review: int
    invalid_rows: int


class MemberImportPreviewOut(BaseModel):
    requires_confirmation: bool
    auto_apply: bool
    summary: MemberImportSummaryOut
    rows: list[MemberImportRowOut]
    action_id: str | None


class MergeMembersPayload(BaseModel):
    primary_id: UUID
    duplicate_id: UUID


_OFFICER_ROLE_LABELS = {
    "president": "회장",
    "vice_president": "부회장",
    "officer": "임원",
}
_ROLE_TO_OFFICER_ROLE = {
    "president": "president",
    "회장": "president",
    "vice_president": "vice_president",
    "부회장": "vice_president",
    "officer": "officer",
    "임원": "officer",
    "총무": "officer",
}
_ROLE_SORT_ORDER = {"president": 0, "vice_president": 1, "officer": 2}


def _to_officer_role(role: str | None, is_officer: bool = False) -> str | None:
    if role:
        return _ROLE_TO_OFFICER_ROLE.get(role.strip(), "officer")
    return "officer" if is_officer else None


def _to_storage_role(officer_role: str | None, fallback: str | None = None) -> str | None:
    if officer_role:
        return _OFFICER_ROLE_LABELS.get(officer_role.strip(), "임원")
    if fallback:
        return _OFFICER_ROLE_LABELS.get(fallback.strip(), fallback)
    return None


def _normalize_member_payload(data: dict[str, Any]) -> dict[str, Any]:
    if data.get("joined_term") and not data.get("term_code"):
        from app.services.membership_fee_policy import normalize_term
        data["term_code"] = normalize_term(data.get("joined_term"))

    is_officer_supplied = "is_officer" in data
    officer_role_supplied = "officer_role" in data
    is_officer = data.pop("is_officer", None)
    officer_role = data.pop("officer_role", None)

    if officer_role_supplied:
        if officer_role:
            data["role"] = _to_storage_role(str(officer_role))
            data["is_executive"] = True
        else:
            data["role"] = None
            if is_officer_supplied:
                data["is_executive"] = bool(is_officer)

    if is_officer_supplied:
        data["is_executive"] = bool(is_officer)
        if not is_officer:
            data["role"] = None
        elif not data.get("role"):
            data["role"] = "임원"

    if data.get("role") in _OFFICER_ROLE_LABELS:
        data["role"] = _to_storage_role(data["role"])
        data["is_executive"] = True

    if data.get("role") in ("회장", "부회장", "임원", "총무"):
        data["is_executive"] = True

    return data


def _role_sort_key(m: Member) -> tuple:
    """Sort key: executives first (by specific title), then regular members."""
    officer_role = _to_officer_role(m.role, bool(m.is_executive))
    if m.is_executive:
        return (0, _ROLE_SORT_ORDER.get(officer_role or "", 9), m.name or "")
    return (1, 9, m.name or "")


@router.get("", response_model=list[MemberRead])
def list_members(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    status: str | None = None,
    q: str | None = None,
    is_executive: bool | None = Query(default=None),
    role: str | None = None,
    is_officer: bool | None = Query(default=None),
    officer_role: str | None = None,
    db: Session = Depends(get_db),
) -> list[Member]:
    statement = select(Member)
    if status:
        statement = statement.where(Member.status == status)
    officer_filter = is_officer if is_officer is not None else is_executive
    if officer_filter is not None:
        statement = statement.where(Member.is_executive == officer_filter)
    role_filter = officer_role or role
    if role_filter:
        storage_role = _to_storage_role(role_filter, role_filter)
        if _to_officer_role(storage_role) == "officer":
            statement = statement.where(Member.is_executive == True)  # noqa: E712
            statement = statement.where(
                or_(Member.role.is_(None), ~Member.role.in_(["회장", "부회장", "president", "vice_president"]))
            )
        else:
            statement = statement.where(Member.role == storage_role)
    if q:
        pattern = f"%{q}%"
        statement = statement.where(
            or_(
                Member.name.ilike(pattern),
                Member.student_id.ilike(pattern),
                Member.department.ilike(pattern),
            )
        )
    rows = list(db.scalars(statement.offset(skip).limit(limit)))
    # Sort: executives first, then by role priority, then name
    rows.sort(key=_role_sort_key)
    return rows


@router.post("", response_model=MemberRead)
def create_member(payload: MemberCreate, db: Session = Depends(get_db)) -> Member:
    if payload.student_id and db.scalar(
        select(Member).where(Member.student_id == payload.student_id)
    ):
        raise HTTPException(status_code=400, detail="student_id already exists")
    data = _normalize_member_payload(payload.model_dump(exclude_unset=True))
    member = Member(**data)
    db.add(member)
    commit_or_400(db, "Could not create member")
    db.refresh(member)
    return member


# ---------------------------------------------------------------------------
# Task 26: Static paths BEFORE parameterised /{member_id} to avoid UUID
# parsing conflicts
# ---------------------------------------------------------------------------

ALLOWED_IMPORT_EXTENSIONS = {".xls", ".xlsx", ".csv"}


@router.post("/import/preview", response_model=MemberImportPreviewOut)
async def preview_member_import(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> MemberImportPreviewOut:
    """Preview member roster import without modifying DB (Task 26)."""
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_IMPORT_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"지원하지 않는 파일 형식: {suffix}")

    file_bytes = await file.read()
    filename = file.filename or "members.xlsx"

    try:
        from app.services.member_import_service import preview_member_import as svc_preview
        rows, summary = svc_preview(db, file_bytes, filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"파일 처리 중 오류: {e}")

    # Create Proposed Action so confirm can apply
    from app.services.assistant_action_service import create_action_proposal
    proposal = create_action_proposal(
        db,
        action_type="member_import",
        source="members_page",
        activity_id=None,
        payload={
            "rows": [
                {
                    "row_index": r.row_index,
                    "name": r.name,
                    "student_id": r.student_id,
                    "department": r.department,
                    "phone": r.phone,
                    "email": r.email,
                    "gender": r.gender,
                    "grade": r.grade,
                    "birth_year": r.birth_year,
                    "joined_term": r.joined_term,
                    "term_code": getattr(r, "term_code", None),
                    "is_executive": r.is_executive,
                    "role": r.role,
                    "is_officer": r.is_executive,
                    "officer_role": _to_officer_role(r.role, r.is_executive),
                    "action": r.action,
                    "matched_member_id": r.matched_member_id,
                }
                for r in rows
            ]
        },
        preview={
            "total_rows": summary.total_rows,
            "new_members": summary.new_members,
            "updates": summary.updates,
        },
        confidence=1.0,
        risk_level="medium",
    )

    return MemberImportPreviewOut(
        requires_confirmation=True,
        auto_apply=False,
        summary=MemberImportSummaryOut(
            total_rows=summary.total_rows,
            new_members=summary.new_members,
            updates=summary.updates,
            duplicate_candidates=summary.duplicate_candidates,
            needs_review=summary.needs_review,
            invalid_rows=summary.invalid_rows,
        ),
        rows=[
            MemberImportRowOut(
                row_index=r.row_index,
                name=r.name,
                student_id=r.student_id,
                department=r.department,
                phone=r.phone,
                email=r.email,
                gender=r.gender,
                grade=r.grade,
                birth_year=r.birth_year,
                joined_term=r.joined_term,
                term_code=getattr(r, "term_code", None),
                is_executive=r.is_executive,
                role=r.role,
                is_officer=r.is_executive,
                officer_role=_to_officer_role(r.role, r.is_executive),
                action=r.action,
                matched_member_id=r.matched_member_id,
                diff=r.diff,
                reason=r.reason,
                available_actions=r.available_actions,
            )
            for r in rows
        ],
        action_id=str(proposal.id),
    )


@router.get("/duplicates")
def get_duplicate_candidates(db: Session = Depends(get_db)) -> list[dict]:
    """Return groups of members that are likely duplicates (Task 26)."""
    from app.services.member_merge_service import find_duplicate_candidates
    groups = find_duplicate_candidates(db)
    return [{"reason": g.reason, "members": g.members} for g in groups]


@router.post("/merge")
def merge_members_endpoint(
    payload: MergeMembersPayload,
    db: Session = Depends(get_db),
) -> dict:
    """Merge a duplicate member into the primary (Task 26)."""
    from app.services.member_merge_service import merge_members

    try:
        result = merge_members(db, payload.primary_id, payload.duplicate_id)
        db.commit()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"ok": True, **result}


@router.get("/{member_id}/summary")
def get_member_summary(member_id: UUID, db: Session = Depends(get_db)) -> dict:
    """Return member profile + activity/payment history."""
    member: Member = get_or_404(db, Member, member_id, "Member")

    # Participated activities (via ActivityParticipant)
    participants = list(db.scalars(
        select(ActivityParticipant)
        .where(ActivityParticipant.member_id == member_id)
    ))
    activity_report_ids = [p.activity_report_id for p in participants]
    activities = []
    if activity_report_ids:
        reports = list(db.scalars(
            select(ActivityReport).where(ActivityReport.id.in_(activity_report_ids))
        ))
        for r in reports:
            p_row = next((p for p in participants if p.activity_report_id == r.id), None)
            activities.append({
                "id": str(r.id),
                "title": r.title,
                "activity_date": str(r.activity_date) if r.activity_date else None,
                "location": r.location,
                "status": r.status,
                "role": p_row.role if p_row else None,
            })

    # All payment records for this member
    payment_records = list(db.scalars(
        select(PaymentRecord).where(PaymentRecord.member_id == member_id)
    ))
    membership_payments = [
        {"id": str(r.id), "period": r.period, "required_amount": r.required_amount,
         "paid_amount": r.paid_amount, "status": r.status}
        for r in payment_records if r.payment_type == "membership_fee"
    ]
    activity_fee_payments = [
        {"id": str(r.id), "period": r.period, "payment_type": r.payment_type,
         "required_amount": r.required_amount, "paid_amount": r.paid_amount, "status": r.status}
        for r in payment_records if r.payment_type == "activity_fee"
    ]

    unpaid_membership = sum(1 for r in payment_records if r.payment_type == "membership_fee" and r.status == "unpaid")
    unpaid_activity = sum(1 for r in payment_records if r.payment_type == "activity_fee" and r.status == "unpaid")

    return {
        "member": {
            "id": str(member.id),
            "name": member.name,
            "student_id": member.student_id,
            "department": member.department,
            "phone": member.phone,
            "email": member.email,
            "status": member.status,
            "memo": member.memo,
            "gender": getattr(member, "gender", None),
            "grade": getattr(member, "grade", None),
            "birth_year": getattr(member, "birth_year", None),
            "joined_term": getattr(member, "joined_term", None),
            "term_code": getattr(member, "term_code", None),
            "is_executive": getattr(member, "is_executive", False),
            "role": getattr(member, "role", None),
            "is_officer": getattr(member, "is_executive", False),
            "officer_role": _to_officer_role(getattr(member, "role", None), getattr(member, "is_executive", False)),
        },
        "activities": activities,
        "membership_payments": membership_payments,
        "activity_fee_payments": activity_fee_payments,
        "summary": {
            "activity_count": len(activities),
            "membership_paid_count": sum(1 for r in payment_records if r.payment_type == "membership_fee" and r.status == "paid"),
            "unpaid_membership_count": unpaid_membership,
            "unpaid_activity_fee_count": unpaid_activity,
        },
    }


# ---------------------------------------------------------------------------
# /{member_id} parameterised routes come AFTER all static paths
# ---------------------------------------------------------------------------

@router.get("/{member_id}", response_model=MemberRead)
def get_member(member_id: UUID, db: Session = Depends(get_db)) -> Member:
    return get_or_404(db, Member, member_id, "Member")


@router.patch("/{member_id}", response_model=MemberRead)
def update_member(
    member_id: UUID,
    payload: MemberUpdate,
    db: Session = Depends(get_db),
) -> Member:
    member = get_or_404(db, Member, member_id, "Member")
    data = _normalize_member_payload(payload.model_dump(exclude_unset=True))
    if "student_id" in data and data["student_id"]:
        duplicate = db.scalar(
            select(Member).where(
                Member.student_id == data["student_id"],
                Member.id != member_id,
            )
        )
        if duplicate:
            raise HTTPException(status_code=400, detail="student_id already exists")
    for key, value in data.items():
        if hasattr(member, key):
            setattr(member, key, value)
    commit_or_400(db, "Could not update member")
    db.refresh(member)
    return member


@router.delete("/{member_id}", response_model=MemberRead)
def delete_member(member_id: UUID, db: Session = Depends(get_db)) -> Member:
    member = get_or_404(db, Member, member_id, "Member")
    member.status = "inactive"
    commit_or_400(db, "Could not deactivate member")
    db.refresh(member)
    return member


@router.post("/{member_id}/deactivate", response_model=MemberRead)
def deactivate_member(member_id: UUID, db: Session = Depends(get_db)) -> Member:
    """Explicit deactivate endpoint (Task 26). Same as DELETE but semantically clearer."""
    member = get_or_404(db, Member, member_id, "Member")
    member.status = "inactive"
    commit_or_400(db, "Could not deactivate member")
    db.refresh(member)
    return member


@router.post("/{member_id}/restore", response_model=MemberRead)
def restore_member(member_id: UUID, db: Session = Depends(get_db)) -> Member:
    """Restore an inactive member to active status (Task 26)."""
    member = get_or_404(db, Member, member_id, "Member")
    if member.status != "inactive":
        raise HTTPException(status_code=400, detail="Member is not inactive")
    member.status = "active"
    commit_or_400(db, "Could not restore member")
    db.refresh(member)
    return member
