"""Member Import Service (Task 26 + booster).

Handles preview + confirm for the exclusive member roster upload flow.
Supports the actual Oui Parfum member roster Excel format:

  이름 / 성별 / 학과 / 학년 / 학번 / 출생년도 / 전화번호 / 가입 시기 / 임원 여부

Policy:
  preview_member_import  → reads file, classifies rows, NO DB write
  apply_member_import_action → called on confirm, creates/updates Members only
  activity_form_imports  → NEVER creates Members (enforced in google_form_import_service)
"""
from __future__ import annotations

import io
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import UUID

import pandas as pd
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.services.membership_fee_policy import normalize_term


# ---------------------------------------------------------------------------
# Column recognisers — maps raw column headers to semantic keys
# ---------------------------------------------------------------------------

_NAME_COLS = [
    "이름", "성명", "성함", "name",
    "이름을 입력해주세요", "이름(본명)", "성함을 입력해주세요",
]
_STUDENT_ID_COLS = [
    "학번", "학생번호", "student id", "student_id",
    "학번을 입력해주세요", "학번(끝까지)",
    "2.학번", "2. 학번",
]
_DEPT_COLS = [
    "학과", "전공", "department", "major",
    "학부", "소속", "학과/학부", "학과(학부)",
]
_PHONE_COLS = [
    "전화번호", "연락처", "휴대폰", "phone", "tel",
    "휴대폰 번호", "전화번호를 입력해주세요", "연락처를 입력해주세요", "연락처(전화번호)",
]
_EMAIL_COLS = [
    "이메일", "email", "e-mail", "이메일을 입력해주세요", "메일",
]
_GENDER_COLS = [
    "성별", "gender", "sex",
]
_GRADE_COLS = [
    "학년", "grade", "년차",
]
_BIRTH_YEAR_COLS = [
    "출생년도", "생년", "출생연도", "birth_year", "출생", "생년월일", "생년도",
]
_JOINED_TERM_COLS = [
    "가입 시기", "가입시기", "가입 학기", "가입학기", "가입년도", "입부 시기",
    "입부시기", "joined_term", "가입",
]
_EXECUTIVE_COLS = [
    "임원 여부", "임원여부", "임원", "직책", "역할", "role", "is_executive",
    "직위", "officer_role", "is_officer",
]


def _find_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    """Return first matching column via case-insensitive partial match."""
    for col in df.columns:
        col_norm = str(col).strip().lower()
        for cand in candidates:
            if cand.lower() in col_norm or col_norm in cand.lower():
                return col
    return None


# ---------------------------------------------------------------------------
# Normalizers
# ---------------------------------------------------------------------------

def _clean_student_id(raw: Any) -> str | None:
    """Normalize student_id to pure digits.

    Handles: float '.0', spaces, hyphens, Excel-stripped leading zeros.
    """
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return None
    s = str(raw).strip()
    if not s or s.lower() in ("nan", "none", "null", "-"):
        return None
    if s.endswith(".0"):
        s = s[:-2]
    digits = "".join(ch for ch in s if ch.isdigit())
    return digits if digits else None


def _clean_phone(raw: Any) -> str | None:
    """Normalize phone to 010-XXXX-XXXX format.

    Handles 11-digit (01x...) and 10-digit starting with 10 (Excel strips leading 0).
    """
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return None
    s = str(raw).strip()
    if not s or s.lower() in ("nan", "none", "null", "-"):
        return None
    digits = re.sub(r"[^\d]", "", s)
    if len(digits) == 10 and digits.startswith("10"):
        digits = "0" + digits
    if len(digits) == 11 and digits.startswith("01"):
        return f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"
    if len(digits) == 10 and digits.startswith("01"):
        return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
    return digits if digits else None


def _clean_str(raw: Any) -> str | None:
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return None
    s = str(raw).strip()
    return s if s else None


def _clean_birth_year(raw: Any) -> int | None:
    """Parse birth_year from '2006', '2006.0', etc."""
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return None
    s = str(raw).strip()
    if s.endswith(".0"):
        s = s[:-2]
    digits = "".join(ch for ch in s if ch.isdigit())
    if len(digits) == 4:
        try:
            return int(digits)
        except ValueError:
            return None
    return None


def _clean_grade(raw: Any) -> str | None:
    """Normalize grade: '2학년' → '2학년', '2' → '2학년', etc."""
    v = _clean_str(raw)
    if not v:
        return None
    v = v.strip()
    if re.match(r"^\d+$", v):
        return f"{v}학년"
    return v


def _clean_joined_term(raw: Any) -> str | None:
    """Preserve raw joined_term value as-is (e.g., '26-1학기')."""
    return _clean_str(raw)


_EXECUTIVE_NO_VALUES = {"", "-", "x", "n", "no", "false", "아니오", "일반", "일반부원", "일반 부원", "0", "f"}
_EXECUTIVE_GENERIC_YES = {"o", "y", "yes", "true", "1", "예", "임원", "t"}
_EXECUTIVE_TITLED = {"회장", "부회장", "총무", "간부", "부장", "서기", "감사", "president", "vice_president", "officer"}


def _clean_executive_info(raw: Any) -> tuple[bool, str | None]:
    """Parse 임원 여부 into (is_executive, role).

    Returns:
      (False, None)      — X, N, 빈값 → 일반 부원
      (True, "임원")     — O, Y, 예, TRUE → 임원 (generic)
      (True, "회장")     — 회장
      (True, "부회장")   — 부회장
      (True, "총무")     — 총무
      (True, <value>)    — other non-empty, non-no values
    """
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return False, None
    s = str(raw).strip()
    norm = s.lower().replace(" ", "")
    if not norm or norm in _EXECUTIVE_NO_VALUES:
        return False, None
    if norm in _EXECUTIVE_GENERIC_YES:
        return True, "임원"
    if norm == "president":
        return True, "회장"
    if norm == "vice_president":
        return True, "부회장"
    if norm == "officer":
        return True, "임원"
    # Specific title
    if s in _EXECUTIVE_TITLED or norm in {t.lower() for t in _EXECUTIVE_TITLED}:
        return True, s
    # Any other non-empty, non-no string → executive with that title
    return True, s


def _clean_is_executive(raw: Any) -> bool:
    """Backward-compat wrapper: returns bool only."""
    is_exec, _ = _clean_executive_info(raw)
    return is_exec


def _normalize(text: str) -> str:
    return unicodedata.normalize("NFC", text).strip()


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class MemberImportRow:
    row_index: int
    name: str | None
    student_id: str | None
    department: str | None
    phone: str | None
    email: str | None
    # Oui Parfum extended fields
    gender: str | None
    grade: str | None
    birth_year: int | None
    joined_term: str | None
    term_code: str | None
    is_executive: bool
    role: str | None
    # Classification
    action: str  # new_member | update_existing | duplicate_candidate | needs_review | invalid
    matched_member_id: str | None
    diff: dict[str, Any]
    reason: str
    available_actions: list[str] = field(default_factory=list)


@dataclass
class MemberImportSummary:
    total_rows: int
    new_members: int
    updates: int
    duplicate_candidates: int
    needs_review: int
    invalid_rows: int


# ---------------------------------------------------------------------------
# Row classification
# ---------------------------------------------------------------------------

def _classify_row(
    db: Session,
    name: str | None,
    student_id: str | None,
    phone: str | None,
    department: str | None,
    email: str | None,
) -> tuple[str, str | None, dict]:
    """Classify a row and return (action, matched_member_id, diff).

    Priority:
      1. student_id exact  → update_existing or new_member
      2. phone exact       → update_existing
      3. name + dept exact → update_existing (single) or duplicate_candidate
      4. name alone        → needs_review
      5. no identifiers    → invalid
    """
    from app.models.member import Member

    if not name and not student_id and not phone:
        return "invalid", None, {}

    def _build_diff(m) -> dict:
        d: dict = {}
        if student_id and m.student_id and m.student_id != student_id:
            d["student_id"] = {"old": m.student_id, "new": student_id}
        if phone and m.phone and m.phone != phone:
            d["phone"] = {"old": m.phone, "new": phone}
        if department and m.department and m.department != department:
            d["department"] = {"old": m.department, "new": department}
        if email and m.email and m.email != email:
            d["email"] = {"old": m.email, "new": email}
        return d

    # 1. student_id exact
    if student_id:
        m = db.scalar(select(Member).where(Member.student_id == student_id))
        if m:
            return "update_existing", str(m.id), _build_diff(m)

    # 2. phone exact
    if phone:
        m = db.scalar(select(Member).where(Member.phone == phone))
        if m:
            return "update_existing", str(m.id), _build_diff(m)

    # 3. name + department
    if name and department:
        norm_name = _normalize(name)
        results = list(db.scalars(
            select(Member).where(
                and_(Member.name == norm_name, Member.department == department)
            )
        ))
        if len(results) == 1:
            return "update_existing", str(results[0].id), _build_diff(results[0])
        if len(results) > 1:
            return "duplicate_candidate", str(results[0].id), {}

    # 4. name alone
    if name:
        norm_name = _normalize(name)
        results = list(db.scalars(select(Member).where(Member.name == norm_name)))
        if len(results) == 1:
            return "needs_review", str(results[0].id), _build_diff(results[0])
        if len(results) > 1:
            return "duplicate_candidate", str(results[0].id), {}

    return "new_member", None, {}


# ---------------------------------------------------------------------------
# File reader
# ---------------------------------------------------------------------------

def _read_file(file_bytes: bytes, filename: str) -> pd.DataFrame:
    suffix = Path(filename).suffix.lower()
    buf = io.BytesIO(file_bytes)
    if suffix in (".xlsx", ".xls"):
        df = pd.read_excel(buf, dtype=str)
    elif suffix == ".csv":
        df = pd.read_csv(buf, dtype=str)
    else:
        raise ValueError(f"지원하지 않는 파일 형식: {suffix}. 지원: .xls, .xlsx, .csv")
    df = df.dropna(how="all").reset_index(drop=True)
    return df


# ---------------------------------------------------------------------------
# Preview
# ---------------------------------------------------------------------------

def preview_member_import(
    db: Session,
    file_bytes: bytes,
    filename: str,
) -> tuple[list[MemberImportRow], MemberImportSummary]:
    """Parse file and classify each row WITHOUT modifying the DB."""
    df = _read_file(file_bytes, filename)

    name_col = _find_col(df, _NAME_COLS)
    sid_col = _find_col(df, _STUDENT_ID_COLS)
    phone_col = _find_col(df, _PHONE_COLS)
    email_col = _find_col(df, _EMAIL_COLS)
    dept_col = _find_col(df, _DEPT_COLS)
    gender_col = _find_col(df, _GENDER_COLS)
    grade_col = _find_col(df, _GRADE_COLS)
    birth_year_col = _find_col(df, _BIRTH_YEAR_COLS)
    joined_term_col = _find_col(df, _JOINED_TERM_COLS)
    executive_col = _find_col(df, _EXECUTIVE_COLS)

    rows: list[MemberImportRow] = []
    new_members = 0
    updates = 0
    dup_candidates = 0
    needs_review_count = 0
    invalid_rows = 0

    for idx, row_data in df.iterrows():
        name = _clean_str(row_data[name_col]) if name_col else None
        student_id = _clean_student_id(row_data[sid_col]) if sid_col else None
        phone = _clean_phone(row_data[phone_col]) if phone_col else None
        email = _clean_str(row_data[email_col]) if email_col else None
        department = _clean_str(row_data[dept_col]) if dept_col else None
        gender = _clean_str(row_data[gender_col]) if gender_col else None
        grade = _clean_grade(row_data[grade_col]) if grade_col else None
        birth_year = _clean_birth_year(row_data[birth_year_col]) if birth_year_col else None
        joined_term = _clean_joined_term(row_data[joined_term_col]) if joined_term_col else None
        term_code = normalize_term(joined_term)
        if executive_col:
            is_executive, exec_role = _clean_executive_info(row_data[executive_col])
        else:
            is_executive, exec_role = False, None

        action, matched_id, diff = _classify_row(db, name, student_id, phone, department, email)

        available_actions: list[str] = []
        if action == "new_member":
            available_actions = ["create_member"]
        elif action == "update_existing":
            available_actions = ["update_member", "skip"]
        elif action in ("duplicate_candidate", "needs_review"):
            available_actions = ["link_existing", "create_new", "skip"]
        elif action == "invalid":
            available_actions = ["skip"]

        reason_map = {
            "new_member": "기존 부원 없음 → 신규 추가",
            "update_existing": "student_id/phone 일치 → 기존 부원 업데이트",
            "duplicate_candidate": "동명이인 존재 → 수동 확인 필요",
            "needs_review": "이름만 일치 → 검토 필요",
            "invalid": "이름/학번/전화번호 없음 → 건너뜀",
        }

        if action == "new_member":
            new_members += 1
        elif action == "update_existing":
            updates += 1
        elif action == "duplicate_candidate":
            dup_candidates += 1
        elif action == "needs_review":
            needs_review_count += 1
        elif action == "invalid":
            invalid_rows += 1

        rows.append(MemberImportRow(
            row_index=int(idx) + 2,
            name=name,
            student_id=student_id,
            department=department,
            phone=phone,
            email=email,
            gender=gender,
            grade=grade,
            birth_year=birth_year,
            joined_term=joined_term,
            term_code=term_code,
            is_executive=is_executive,
            role=exec_role,
            action=action,
            matched_member_id=matched_id,
            diff=diff,
            reason=reason_map.get(action, ""),
            available_actions=available_actions,
        ))

    summary = MemberImportSummary(
        total_rows=len(rows),
        new_members=new_members,
        updates=updates,
        duplicate_candidates=dup_candidates,
        needs_review=needs_review_count,
        invalid_rows=invalid_rows,
    )
    return rows, summary


# ---------------------------------------------------------------------------
# Apply (called from confirm_action_proposal)
# ---------------------------------------------------------------------------

def apply_member_import_action(db: Session, payload: dict) -> dict:
    """Apply a confirmed Proposed Action — creates/updates Members only."""
    from app.models.member import Member

    rows_raw: list[dict] = payload.get("rows", [])
    created = 0
    updated = 0
    skipped = 0

    for r in rows_raw:
        action = r.get("action")
        if action == "invalid":
            skipped += 1
            continue

        name = r.get("name")
        student_id = r.get("student_id")
        phone = r.get("phone")
        email = r.get("email")
        department = r.get("department")
        gender = r.get("gender")
        grade = r.get("grade")
        birth_year = r.get("birth_year")
        joined_term = r.get("joined_term")
        term_code = r.get("term_code") or normalize_term(joined_term)
        is_executive = bool(r.get("is_executive", False))
        matched_id_str = r.get("matched_member_id")

        role = r.get("role")
        if action == "new_member":
            if not name:
                skipped += 1
                continue
            member = Member(
                name=_normalize(name),
                student_id=student_id,
                phone=phone,
                email=email,
                department=department,
                gender=gender,
                grade=grade,
                birth_year=birth_year,
                joined_term=joined_term,
                term_code=term_code,
                is_executive=is_executive,
                role=role,
                status="active",
            )
            db.add(member)
            created += 1

        elif action == "update_existing" and matched_id_str:
            member = db.get(Member, UUID(matched_id_str))
            if not member:
                skipped += 1
                continue
            changed = False
            # Backfill missing fields only (don't overwrite student_id)
            if not member.phone and phone:
                member.phone = phone
                changed = True
            if not member.email and email:
                member.email = email
                changed = True
            if not member.department and department:
                member.department = department
                changed = True
            if not member.gender and gender:
                member.gender = gender
                changed = True
            if not member.grade and grade:
                member.grade = grade
                changed = True
            if not member.birth_year and birth_year:
                member.birth_year = birth_year
                changed = True
            if not member.joined_term and joined_term:
                member.joined_term = joined_term
                changed = True
            if not getattr(member, "term_code", None) and term_code:
                member.term_code = term_code
                changed = True
            # Role update logic — don't overwrite 회장/부회장 with generic "임원"
            _high_roles = {"회장", "부회장", "총무"}
            if is_executive:
                if not member.role:
                    member.role = role or "임원"
                    member.is_executive = True
                    changed = True
                elif member.role in _high_roles and role not in _high_roles:
                    # Keep the more specific title
                    pass
                elif role and role not in _high_roles and member.role not in _high_roles:
                    if member.role != role:
                        member.role = role
                        changed = True
            elif not is_executive and member.is_executive and member.role in _high_roles:
                # Upload says X but member is 회장/부회장 → skip (conflict)
                pass
            if changed:
                updated += 1
            else:
                skipped += 1

        else:
            # needs_review / duplicate_candidate / explicit skip
            skipped += 1

    db.flush()
    return {
        "created_members": created,
        "updated_members": updated,
        "skipped_rows": skipped,
    }
