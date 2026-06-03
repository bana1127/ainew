"""Google Form Import Service.

Handles reading Excel/CSV files that are exported from Google Forms and:
  - Classifying the form type
  - Normalizing rows (name, student_id, phone, email, raw_response)
  - Matching / creating Member records
  - Creating / updating ActivityParticipant records
  - Saving ActivityFeedback records for feedback forms
"""
from __future__ import annotations

import io
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

import pandas as pd
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.services.excel_form_classifier import (
    FormClassificationResult,
    classify_excel_form,
)


# ---------------------------------------------------------------------------
# Column name normalisers — maps raw column names to semantic keys
# ---------------------------------------------------------------------------

_NAME_COLS = ["이름", "성명", "name"]
_STUDENT_ID_COLS = ["학번", "학생번호", "student id", "student_id"]
_PHONE_COLS = ["전화번호", "연락처", "휴대폰", "phone", "tel"]
_EMAIL_COLS = ["이메일", "email"]
_DEPT_COLS = ["학과", "전공", "department", "major"]
_TIMESTAMP_COLS = ["타임스탬프", "신청 시간", "제출 시간", "응답 시간", "timestamp"]


def _find_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    """Find the first matching column name (case-insensitive partial match)."""
    for col in df.columns:
        col_norm = str(col).strip().lower()
        for cand in candidates:
            if cand.lower() in col_norm or col_norm in cand.lower():
                return col
    return None


def _clean_phone(raw: Any) -> str | None:
    if not raw or (isinstance(raw, float) and pd.isna(raw)):
        return None
    s = str(raw).strip()
    digits = re.sub(r"[^\d]", "", s)
    # Excel sometimes strips the leading 0 from phone numbers (reads as integer)
    # e.g. 1056279620 (10 digits, starts with 10) → prepend "0"
    if len(digits) == 10 and digits.startswith("10"):
        digits = "0" + digits
    if len(digits) == 11 and digits.startswith("01"):
        return f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"
    if len(digits) == 10 and digits.startswith("01"):
        return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
    return digits if digits else None


def _clean_student_id(raw: Any) -> str | None:
    """Normalize student_id to a pure digit string.

    Handles:
    - float trailing '.0' (e.g. 2022130026.0 → "2022130026")
    - leading/trailing spaces
    - non-digit separators (e.g. "2022-130026" → "2022130026")
    - Excel reads as float: 2022130026.0 → str → clean
    """
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return None
    s = str(raw).strip()
    if not s:
        return None
    # Remove float trailing '.0' before extracting digits
    if s.endswith(".0"):
        s = s[:-2]
    # Extract only digits for a stable, canonical form
    digits = "".join(ch for ch in s if ch.isdigit())
    return digits if digits else None


def _clean_str(raw: Any) -> str | None:
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return None
    s = str(raw).strip()
    return s if s else None


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ImportRow:
    row_index: int
    name: str | None
    student_id: str | None
    phone: str | None
    email: str | None
    department: str | None
    submitted_at: str | None
    member_match_status: str  # matched | new | needs_review
    member_id: str | None  # existing member id if matched
    participant_action: str  # create | update | skip
    participant_status: str  # applied | completed
    raw_response: dict[str, Any] = field(default_factory=dict)


@dataclass
class ImportActivityContext:
    mode: str  # linked | candidate | none
    activity_id: str | None = None
    activity_title: str | None = None


@dataclass
class ImportSummary:
    total_rows: int
    matched_members: int
    new_member_candidates: int
    needs_review: int
    existing_participants: int
    new_participants: int


@dataclass
class ImportPreviewResult:
    import_id: str
    form_type: str
    confidence: float
    matched_columns: list[str]
    activity_context: ImportActivityContext
    summary: ImportSummary
    rows: list[ImportRow]
    requires_confirmation: bool


@dataclass
class ImportApplyResult:
    ok: bool
    activity_id: str
    form_type: str
    created_members: int
    updated_members: int
    created_participants: int
    updated_participants: int
    saved_feedbacks: int


# ---------------------------------------------------------------------------
# Member matching
# ---------------------------------------------------------------------------

def _match_member(
    db: Session,
    name: str | None,
    student_id: str | None,
    phone: str | None,
    department: str | None,
) -> tuple:
    """Try to find an existing member. Returns (member, match_status)."""
    from app.models.member import Member
    # 1. student_id exact
    if student_id:
        m = db.scalar(select(Member).where(Member.student_id == student_id))
        if m:
            return m, "matched"

    # 2. phone exact
    if phone:
        m = db.scalar(select(Member).where(Member.phone == phone))
        if m:
            return m, "matched"

    # 3. name + department exact
    if name and department:
        results = list(
            db.scalars(
                select(Member).where(
                    and_(Member.name == name, Member.department == department)
                )
            )
        )
        if len(results) == 1:
            return results[0], "matched"
        if len(results) > 1:
            return results[0], "needs_review"

    # 4. name match
    if name:
        results = list(db.scalars(select(Member).where(Member.name == name)))
        if len(results) == 1:
            # Check department if available
            if department and results[0].department and department not in results[0].department:
                return results[0], "needs_review"
            return results[0], "matched"
        elif len(results) > 1:
            return results[0], "needs_review"

    return None, "new"


# ---------------------------------------------------------------------------
# Row normaliser
# ---------------------------------------------------------------------------

def _normalise_rows(
    df: pd.DataFrame,
    form_type: str,
    db: Session,
) -> tuple[list[ImportRow], int, int, int, int]:
    """Convert DataFrame rows to ImportRow list.

    Returns (rows, matched_count, new_count, needs_review_count).
    """
    name_col = _find_col(df, _NAME_COLS)
    sid_col = _find_col(df, _STUDENT_ID_COLS)
    phone_col = _find_col(df, _PHONE_COLS)
    email_col = _find_col(df, _EMAIL_COLS)
    dept_col = _find_col(df, _DEPT_COLS)
    ts_col = _find_col(df, _TIMESTAMP_COLS)

    participant_status_map = {
        "activity_application_form": "applied",
        "member_roster": "confirmed",
        "activity_feedback_form": "completed",
    }
    participant_status = participant_status_map.get(form_type, "applied")

    rows: list[ImportRow] = []
    matched_count = 0
    new_count = 0
    needs_review_count = 0

    for idx, row in df.iterrows():
        name = _clean_str(row[name_col]) if name_col else None
        student_id = _clean_student_id(row[sid_col]) if sid_col else None
        phone = _clean_phone(row[phone_col]) if phone_col else None
        email = _clean_str(row[email_col]) if email_col else None
        department = _clean_str(row[dept_col]) if dept_col else None
        submitted_at_raw = _clean_str(row[ts_col]) if ts_col else None

        # Build raw_response: all non-identity columns
        identity_cols = {c for c in [name_col, sid_col, phone_col, email_col, dept_col, ts_col] if c}
        raw_resp: dict[str, Any] = {}
        for col in df.columns:
            if col not in identity_cols:
                val = row[col]
                if not (isinstance(val, float) and pd.isna(val)):
                    raw_resp[str(col)] = str(val) if val is not None else None

        if not name and not student_id and not phone:
            continue  # skip empty rows

        member, match_status = _match_member(db, name, student_id, phone, department)

        if match_status == "matched":
            matched_count += 1
        elif match_status == "needs_review":
            needs_review_count += 1
        else:
            new_count += 1

        rows.append(ImportRow(
            row_index=int(idx) + 2,  # 1-based row number (header = row 1)
            name=name,
            student_id=student_id,
            phone=phone,
            email=email,
            department=department,
            submitted_at=submitted_at_raw,
            member_match_status=match_status,
            member_id=str(member.id) if member else None,
            participant_action="create",  # will be updated below
            participant_status=participant_status,
            raw_response=raw_resp,
        ))

    return rows, matched_count, new_count, needs_review_count


# ---------------------------------------------------------------------------
# Read file bytes → DataFrame
# ---------------------------------------------------------------------------

def _read_file(file_bytes: bytes, filename: str) -> pd.DataFrame:
    """Parse uploaded bytes into a DataFrame."""
    suffix = Path(filename).suffix.lower()
    buf = io.BytesIO(file_bytes)
    if suffix in (".xlsx", ".xls"):
        df = pd.read_excel(buf, dtype=str)
    elif suffix == ".csv":
        df = pd.read_csv(buf, dtype=str)
    else:
        raise ValueError(f"지원하지 않는 파일 형식: {suffix}")
    # Drop fully empty rows
    df = df.dropna(how="all").reset_index(drop=True)
    return df


# ---------------------------------------------------------------------------
# Preview
# ---------------------------------------------------------------------------

def preview_import(
    db: Session,
    file_bytes: bytes,
    filename: str,
    activity_id: str | None = None,
    form_stage: str = "auto",
) -> ImportPreviewResult:
    df = _read_file(file_bytes, filename)
    headers = [str(c) for c in df.columns.tolist()]

    classification: FormClassificationResult = classify_excel_form(headers, filename)
    form_type = classification.form_type

    # Override if user supplied explicit stage hint
    if form_stage == "before":
        form_type = "activity_application_form"
    elif form_stage == "after":
        form_type = "activity_feedback_form"
    elif form_stage == "roster":
        form_type = "member_roster"

    from app.models.activity import ActivityParticipant, ActivityReport
    from app.models.member import Member
    # Resolve activity context
    activity_ctx = ImportActivityContext(mode="none")
    if activity_id:
        report = db.get(ActivityReport, UUID(activity_id))
        if report:
            activity_ctx = ImportActivityContext(
                mode="linked",
                activity_id=str(report.id),
                activity_title=report.title,
            )
        else:
            activity_ctx = ImportActivityContext(mode="none")
    else:
        # Try to find candidate activities from filename / form type
        from app.agents.activity_resolver import resolve_activity_context
        res = resolve_activity_context(
            db=db,
            message=filename,
            file_names=[filename],
            activity_id=None,
            activity_mode="auto",
        )
        if res.mode == "linked" and res.activity_id:
            activity_ctx = ImportActivityContext(
                mode="candidate",
                activity_id=res.activity_id,
                activity_title=res.activity_title,
            )

    rows, matched, new, needs_review = _normalise_rows(df, form_type, db)

    # Mark participants with existing records
    existing_participants = 0
    if activity_ctx.activity_id:
        act_id = UUID(activity_ctx.activity_id)
        for r in rows:
            if r.member_id:
                existing_p = db.scalar(
                    select(ActivityParticipant).where(
                        and_(
                            ActivityParticipant.activity_report_id == act_id,
                            ActivityParticipant.member_id == UUID(r.member_id),
                        )
                    )
                )
                if existing_p:
                    r.participant_action = "update"
                    existing_participants += 1

    new_participants = len(rows) - existing_participants

    summary = ImportSummary(
        total_rows=len(rows),
        matched_members=matched,
        new_member_candidates=new,
        needs_review=needs_review,
        existing_participants=existing_participants,
        new_participants=new_participants,
    )

    import_id = f"preview-{uuid.uuid4().hex[:12]}"

    return ImportPreviewResult(
        import_id=import_id,
        form_type=form_type,
        confidence=classification.confidence,
        matched_columns=classification.matched_columns,
        activity_context=activity_ctx,
        summary=summary,
        rows=rows,
        requires_confirmation=True,
    )


# ---------------------------------------------------------------------------
# Apply
# ---------------------------------------------------------------------------

def apply_import(
    db: Session,
    activity_id: str,
    form_type: str,
    rows: list[ImportRow],
) -> ImportApplyResult:
    from app.models.activity import ActivityParticipant, ActivityReport
    from app.models.member import Member

    try:
        act_uuid = UUID(activity_id)
    except ValueError:
        raise ValueError(f"잘못된 activity_id: {activity_id}")

    report = db.get(ActivityReport, act_uuid)
    if not report:
        raise ValueError(f"활동을 찾을 수 없습니다: {activity_id}")

    created_members = 0
    updated_members = 0
    created_participants = 0
    updated_participants = 0
    saved_feedbacks = 0

    participant_status_map = {
        "activity_application_form": "applied",
        "member_roster": "confirmed",
        "activity_feedback_form": "completed",
    }
    participant_status = participant_status_map.get(form_type, "applied")

    for row in rows:
        # ── Member upsert ──────────────────────────────────────────────────
        member: Member | None = None

        if row.member_id:
            member = db.get(Member, UUID(row.member_id))
            if member:
                # Update only missing fields
                changed = False
                if not member.student_id and row.student_id:
                    member.student_id = row.student_id
                    changed = True
                if not member.phone and row.phone:
                    member.phone = row.phone
                    changed = True
                if not member.email and row.email:
                    member.email = row.email
                    changed = True
                if not member.department and row.department:
                    member.department = row.department
                    changed = True
                if changed:
                    updated_members += 1
        else:
            # Task 26: do NOT auto-create Members from activity import.
            # Unmatched rows are silently skipped here; they appear as
            # "unregistered_candidate" in the preview summary.
            continue

        if not member:
            continue

        # ── ActivityParticipant upsert ─────────────────────────────────────
        existing_p = db.scalar(
            select(ActivityParticipant).where(
                and_(
                    ActivityParticipant.activity_report_id == act_uuid,
                    ActivityParticipant.member_id == member.id,
                )
            )
        )

        if existing_p:
            # Update status and raw_response
            if hasattr(existing_p, "status"):
                existing_p.status = participant_status
            if hasattr(existing_p, "raw_response_json"):
                existing_p.raw_response_json = row.raw_response
            updated_participants += 1
            participant = existing_p
        else:
            participant = ActivityParticipant(
                activity_report_id=act_uuid,
                member_id=member.id,
                role="participant",
            )
            if hasattr(participant, "status"):
                participant.status = participant_status
            if hasattr(participant, "raw_response_json"):
                participant.raw_response_json = row.raw_response
            db.add(participant)
            db.flush()
            created_participants += 1

        # ── ActivityFeedback for feedback forms ────────────────────────────
        if form_type == "activity_feedback_form" and row.raw_response:
            from app.models.activity_feedback import ActivityFeedback
            feedback = ActivityFeedback(
                activity_id=act_uuid,
                member_id=member.id,
                response_type="activity_feedback_form",
                raw_response_json=row.raw_response,
                submitted_at=_parse_submitted_at(row.submitted_at),
            )
            db.add(feedback)
            saved_feedbacks += 1

    db.commit()

    return ImportApplyResult(
        ok=True,
        activity_id=activity_id,
        form_type=form_type,
        created_members=created_members,
        updated_members=updated_members,
        created_participants=created_participants,
        updated_participants=updated_participants,
        saved_feedbacks=saved_feedbacks,
    )


def _parse_submitted_at(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return pd.to_datetime(raw).to_pydatetime()
    except Exception:
        return None
