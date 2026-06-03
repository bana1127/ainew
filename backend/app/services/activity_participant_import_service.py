"""Activity Participant Import Service.

preview  → AssistantActionProposal 생성 (DB 미반영)
confirm  → proposal 기반으로 ActivityParticipant 생성/수정
cancel   → proposal 취소

Match status values:
  matched_member        - student_id 또는 phone 기준 확실한 매칭
  needs_review          - name+dept 매칭이지만 불확실 (사용자 확인 필요)
  duplicate_candidate   - 동명이인 (사용자가 선택해야 함)
  unregistered_candidate - 매칭 실패
  already_participant   - 이미 이 활동의 참여자

Participant status values:
  will_create       - confirm 시 생성 예정
  will_update       - confirm 시 갱신 예정
  already_participant - 이미 참여자 (변화 없거나 update)
  needs_review      - 사용자 선택 필요
  invalid           - 처리 불가

Available actions for unregistered_candidate:
  link_existing_member  - 기존 부원에 연결 (수동 선택 후)
  create_new_member     - 새 부원으로 등록
  mark_external         - 외부인으로 유지
  ignore                - 무시
"""
from __future__ import annotations

import io
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import UUID

import pandas as pd
from sqlalchemy import and_, select
from sqlalchemy.orm import Session


# ---------------------------------------------------------------------------
# Column name normalizers — extended for Task 27
# ---------------------------------------------------------------------------

_NAME_COLS = [
    "이름", "성명", "성함", "이름을 입력해주세요", "성함을 입력해주세요", "name",
]
_STUDENT_ID_COLS = [
    "학번", "학생번호", "학번을 입력해주세요", "2.학번", "2. 학번",
    "학번(끝까지)", "끝까지 적어주세요", "student id", "student_id",
]
_PHONE_COLS = [
    "전화번호", "연락처", "휴대폰", "휴대폰 번호", "전화번호를 입력해주세요",
    "phone", "tel",
]
_DEPT_COLS = [
    "학과", "학부", "전공", "소속", "학과/학부", "department", "major",
]
_TIMESTAMP_COLS = ["타임스탬프", "신청 시간", "제출 시간", "응답 시간", "timestamp"]


def _find_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
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
    if len(digits) == 10 and digits.startswith("10"):
        digits = "0" + digits
    if len(digits) == 11 and digits.startswith("01"):
        return f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"
    if len(digits) == 10 and digits.startswith("01"):
        return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
    return digits if digits else None


def _clean_student_id(raw: Any) -> str | None:
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return None
    s = str(raw).strip()
    if not s:
        return None
    if s.endswith(".0"):
        s = s[:-2]
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
class ImportPreviewRow:
    row_index: int
    name: str | None
    student_id: str | None
    department: str | None
    phone: str | None
    match_status: str  # matched_member | needs_review | duplicate_candidate | unregistered_candidate | already_participant
    matched_member_id: str | None
    matched_member_name: str | None
    participant_status: str  # will_create | will_update | already_participant | needs_review | invalid
    action: str  # link_existing_member | needs_user_selection | already_exists | invalid
    available_actions: list[str]
    reason: str
    selected_action: str | None = None  # set by user for unregistered_candidate rows
    raw_response: dict[str, Any] = field(default_factory=dict)


@dataclass
class ImportPreviewSummary:
    total_rows: int
    matched_members: int
    unregistered_candidates: int
    duplicate_candidates: int
    needs_review: int
    invalid_rows: int
    already_participants: int
    will_create_participants: int
    will_update_participants: int


@dataclass
class ImportPreviewResult:
    activity_id: str
    requires_confirmation: bool
    auto_apply: bool
    summary: ImportPreviewSummary
    rows: list[ImportPreviewRow]
    action_id: str  # AssistantActionProposal id


@dataclass
class ImportConfirmResult:
    ok: bool
    activity_id: str
    created_participants: int
    updated_participants: int
    already_participants: int
    external_participants: int
    ignored_rows: int
    created_members: int


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
    """Returns (member_or_list, match_status).

    match_status: matched_member | needs_review | duplicate_candidate | unregistered_candidate
    When multiple candidates found, returns (list_of_members, duplicate_candidate).
    """
    from app.models.member import Member

    # 1. student_id exact
    if student_id:
        m = db.scalar(select(Member).where(Member.student_id == student_id))
        if m:
            return m, "matched_member"

    # 2. phone exact
    if phone:
        m = db.scalar(select(Member).where(Member.phone == phone))
        if m:
            return m, "matched_member"

    # 3. name + department
    if name and department:
        results = list(
            db.scalars(
                select(Member).where(
                    and_(Member.name == name, Member.department == department)
                )
            )
        )
        if len(results) == 1:
            return results[0], "matched_member"
        if len(results) > 1:
            return results, "duplicate_candidate"

    # 4. name only
    if name:
        results = list(db.scalars(select(Member).where(Member.name == name)))
        if len(results) == 1:
            return results[0], "needs_review"
        if len(results) > 1:
            return results, "duplicate_candidate"

    return None, "unregistered_candidate"


# ---------------------------------------------------------------------------
# Read file bytes → DataFrame
# ---------------------------------------------------------------------------

def _read_file(file_bytes: bytes, filename: str) -> pd.DataFrame:
    suffix = Path(filename).suffix.lower()
    buf = io.BytesIO(file_bytes)
    if suffix in (".xlsx", ".xls"):
        df = pd.read_excel(buf, dtype=str)
    elif suffix == ".csv":
        df = pd.read_csv(buf, dtype=str)
    else:
        raise ValueError(f"지원하지 않는 파일 형식: {suffix}")
    df = df.dropna(how="all").reset_index(drop=True)
    return df


# ---------------------------------------------------------------------------
# Preview
# ---------------------------------------------------------------------------

def preview_participant_import(
    db: Session,
    file_bytes: bytes,
    filename: str,
    activity_id: UUID,
    file_id: UUID | None = None,
) -> ImportPreviewResult:
    """Parse file, match members, check existing participants.

    Never modifies DB. Creates an AssistantActionProposal for the confirm step.
    """
    from app.models.activity import ActivityParticipant, ActivityReport

    report = db.get(ActivityReport, activity_id)
    if not report:
        raise ValueError(f"활동을 찾을 수 없습니다: {activity_id}")

    df = _read_file(file_bytes, filename)
    name_col = _find_col(df, _NAME_COLS)
    sid_col = _find_col(df, _STUDENT_ID_COLS)
    phone_col = _find_col(df, _PHONE_COLS)
    dept_col = _find_col(df, _DEPT_COLS)

    rows: list[ImportPreviewRow] = []

    matched_count = 0
    unregistered_count = 0
    duplicate_count = 0
    needs_review_count = 0
    invalid_count = 0
    already_participant_count = 0
    will_create_count = 0
    will_update_count = 0

    for idx, row_data in df.iterrows():
        name = _clean_str(row_data[name_col]) if name_col else None
        student_id = _clean_student_id(row_data[sid_col]) if sid_col else None
        phone = _clean_phone(row_data[phone_col]) if phone_col else None
        department = _clean_str(row_data[dept_col]) if dept_col else None

        if not name and not student_id and not phone:
            continue  # skip empty rows

        # Build raw_response
        identity_cols = {c for c in [name_col, sid_col, phone_col, dept_col] if c}
        raw_resp: dict[str, Any] = {}
        for col in df.columns:
            if col not in identity_cols:
                val = row_data[col]
                if not (isinstance(val, float) and pd.isna(val)):
                    raw_resp[str(col)] = str(val) if val is not None else None

        member_or_list, match_status = _match_member(db, name, student_id, phone, department)

        # Handle duplicate_candidate
        if match_status == "duplicate_candidate":
            candidate_list = member_or_list if isinstance(member_or_list, list) else [member_or_list]
            duplicate_count += 1
            rows.append(ImportPreviewRow(
                row_index=int(idx) + 2,
                name=name,
                student_id=student_id,
                department=department,
                phone=phone,
                match_status="duplicate_candidate",
                matched_member_id=None,
                matched_member_name=None,
                participant_status="needs_review",
                action="needs_user_selection",
                available_actions=["link_existing_member", "mark_external", "ignore"],
                reason=f"동명이인 {len(candidate_list)}명",
                raw_response=raw_resp,
            ))
            continue

        member = member_or_list if not isinstance(member_or_list, list) else None

        if match_status in ("matched_member", "needs_review"):
            if match_status == "matched_member":
                matched_count += 1
            else:
                needs_review_count += 1

            # Check if already a participant
            existing_p = db.scalar(
                select(ActivityParticipant).where(
                    and_(
                        ActivityParticipant.activity_report_id == activity_id,
                        ActivityParticipant.member_id == member.id,
                    )
                )
            ) if member else None

            if existing_p:
                already_participant_count += 1
                p_status = "already_participant"
                action = "already_exists"
                reason = "이미 참여자로 등록됨"
                available = []
            else:
                will_create_count += 1
                p_status = "will_create"
                action = "link_existing_member"
                available = ["link_existing_member", "ignore"]
                reason = "student_id 매칭" if student_id and member and member.student_id == student_id else (
                    "phone 매칭" if phone and member and member.phone == phone else "이름+학과 매칭"
                )
                if match_status == "needs_review":
                    reason = f"이름만 매칭 (확인 필요): {reason}"
                    p_status = "needs_review"
                    action = "needs_user_selection"
                    available = ["link_existing_member", "mark_external", "ignore"]

            rows.append(ImportPreviewRow(
                row_index=int(idx) + 2,
                name=name,
                student_id=student_id,
                department=department,
                phone=phone,
                match_status=match_status,
                matched_member_id=str(member.id) if member else None,
                matched_member_name=member.name if member else None,
                participant_status=p_status,
                action=action,
                available_actions=available,
                reason=reason,
                raw_response=raw_resp,
            ))

        else:  # unregistered_candidate
            unregistered_count += 1
            rows.append(ImportPreviewRow(
                row_index=int(idx) + 2,
                name=name,
                student_id=student_id,
                department=department,
                phone=phone,
                match_status="unregistered_candidate",
                matched_member_id=None,
                matched_member_name=None,
                participant_status="needs_review",
                action="needs_user_selection",
                available_actions=["link_existing_member", "create_new_member", "mark_external", "ignore"],
                reason="매칭되는 부원 없음",
                raw_response=raw_resp,
            ))

    summary = ImportPreviewSummary(
        total_rows=len(rows),
        matched_members=matched_count,
        unregistered_candidates=unregistered_count,
        duplicate_candidates=duplicate_count,
        needs_review=needs_review_count,
        invalid_rows=invalid_count,
        already_participants=already_participant_count,
        will_create_participants=will_create_count,
        will_update_participants=0,
    )

    # Store preview in AssistantActionProposal
    from app.services.assistant_action_service import create_action_proposal

    rows_payload = [
        {
            "row_index": r.row_index,
            "name": r.name,
            "student_id": r.student_id,
            "department": r.department,
            "phone": r.phone,
            "match_status": r.match_status,
            "matched_member_id": r.matched_member_id,
            "participant_status": r.participant_status,
            "action": r.action,
            "available_actions": r.available_actions,
            "reason": r.reason,
            "selected_action": r.selected_action,
            "raw_response": r.raw_response,
        }
        for r in rows
    ]

    proposal = create_action_proposal(
        db,
        action_type="participant_import",
        source="activity_detail",
        activity_id=activity_id,
        payload={
            "activity_id": str(activity_id),
            "file_id": str(file_id) if file_id else None,
            "rows": rows_payload,
        },
        preview={
            "activity_id": str(activity_id),
            "activity_title": report.title,
            "summary": {
                "total_rows": summary.total_rows,
                "matched_members": summary.matched_members,
                "unregistered_candidates": summary.unregistered_candidates,
                "duplicate_candidates": summary.duplicate_candidates,
                "needs_review": summary.needs_review,
                "invalid_rows": summary.invalid_rows,
                "already_participants": summary.already_participants,
                "will_create_participants": summary.will_create_participants,
                "will_update_participants": summary.will_update_participants,
            },
        },
        confidence=0.9,
        risk_level="low",
    )

    return ImportPreviewResult(
        activity_id=str(activity_id),
        requires_confirmation=True,
        auto_apply=False,
        summary=summary,
        rows=rows,
        action_id=str(proposal.id),
    )


# ---------------------------------------------------------------------------
# Confirm
# ---------------------------------------------------------------------------

def confirm_participant_import(
    db: Session,
    action_id: UUID,
    row_overrides: list[dict] | None = None,
) -> ImportConfirmResult:
    """Apply the confirmed participant import proposal.

    row_overrides: list of {row_index, selected_action, matched_member_id}
    to override default action per row (user selections for unregistered candidates).
    """
    from app.models.activity import ActivityParticipant, ActivityReport
    from app.models.file import UploadedFile
    from app.models.member import Member
    from app.models.assistant_action import AssistantActionProposal

    proposal = db.get(AssistantActionProposal, action_id)
    if not proposal:
        raise ValueError(f"Action proposal not found: {action_id}")
    if proposal.status != "pending":
        raise ValueError(f"Action proposal is not pending: {proposal.status}")

    payload = proposal.payload_json
    activity_id = UUID(str(payload["activity_id"]))
    file_id_str = payload.get("file_id")
    rows_data: list[dict] = payload.get("rows", [])

    report = db.get(ActivityReport, activity_id)
    if not report:
        raise ValueError(f"활동을 찾을 수 없습니다: {activity_id}")

    # Build override map by row_index
    override_map: dict[int, dict] = {}
    for ov in (row_overrides or []):
        override_map[int(ov["row_index"])] = ov

    created_participants = 0
    updated_participants = 0
    already_participants = 0
    external_participants = 0
    ignored_rows = 0
    created_members = 0

    for row in rows_data:
        row_index = int(row["row_index"])
        # Apply user override if provided
        if row_index in override_map:
            ov = override_map[row_index]
            effective_action = ov.get("selected_action") or row.get("action")
            if ov.get("matched_member_id"):
                row = {**row, "matched_member_id": ov["matched_member_id"]}
        else:
            effective_action = row.get("selected_action") or row.get("action")

        match_status = row.get("match_status", "")
        member_id_str = row.get("matched_member_id")
        name = row.get("name")
        student_id = row.get("student_id")
        phone = row.get("phone")
        department = row.get("department")
        raw_response = row.get("raw_response") or {}

        # --- already_participant: update raw_response only ---
        if effective_action == "already_exists" or row.get("participant_status") == "already_participant":
            if member_id_str:
                existing_p = db.scalar(
                    select(ActivityParticipant).where(
                        and_(
                            ActivityParticipant.activity_report_id == activity_id,
                            ActivityParticipant.member_id == UUID(member_id_str),
                        )
                    )
                )
                if existing_p:
                    if raw_response and hasattr(existing_p, "raw_response_json"):
                        existing_p.raw_response_json = raw_response
                    already_participants += 1
                    continue
            already_participants += 1
            continue

        # --- ignore ---
        if effective_action == "ignore" or effective_action == "needs_user_selection":
            ignored_rows += 1
            continue

        # --- link_existing_member ---
        if effective_action == "link_existing_member":
            if not member_id_str:
                ignored_rows += 1
                continue
            member = db.get(Member, UUID(member_id_str))
            if not member:
                ignored_rows += 1
                continue
            existing_p = db.scalar(
                select(ActivityParticipant).where(
                    and_(
                        ActivityParticipant.activity_report_id == activity_id,
                        ActivityParticipant.member_id == member.id,
                    )
                )
            )
            if existing_p:
                if raw_response and hasattr(existing_p, "raw_response_json"):
                    existing_p.raw_response_json = raw_response
                updated_participants += 1
            else:
                p = ActivityParticipant(
                    activity_report_id=activity_id,
                    member_id=member.id,
                    role="participant",
                    status="applied",
                    raw_response_json=raw_response or None,
                )
                db.add(p)
                created_participants += 1
            continue

        # --- create_new_member ---
        if effective_action == "create_new_member":
            if not name:
                ignored_rows += 1
                continue
            # Create new Member
            new_member = Member(
                name=name,
                student_id=student_id,
                phone=phone,
                department=department,
                status="active",
            )
            db.add(new_member)
            db.flush()
            created_members += 1
            # Create participant
            p = ActivityParticipant(
                activity_report_id=activity_id,
                member_id=new_member.id,
                role="participant",
                status="applied",
                raw_response_json=raw_response or None,
            )
            db.add(p)
            db.flush()
            created_participants += 1
            continue

        # --- mark_external ---
        if effective_action == "mark_external":
            if not name:
                ignored_rows += 1
                continue
            # Duplicate check: same activity + external_name + external_student_id
            dup_q = select(ActivityParticipant).where(
                and_(
                    ActivityParticipant.activity_report_id == activity_id,
                    ActivityParticipant.member_id.is_(None),
                    ActivityParticipant.external_name == name,
                )
            )
            if student_id:
                dup_q = dup_q.where(ActivityParticipant.external_student_id == student_id)
            existing_ext = db.scalar(dup_q)
            if existing_ext:
                already_participants += 1
                continue
            p = ActivityParticipant(
                activity_report_id=activity_id,
                member_id=None,
                external_name=name,
                external_affiliation=department,
                external_student_id=student_id,
                role="external",
                status="applied",
                raw_response_json=raw_response or None,
            )
            db.add(p)
            db.flush()
            external_participants += 1
            created_participants += 1
            continue

        # fallback: ignore
        ignored_rows += 1

    # Update source file category
    if file_id_str:
        try:
            file_record = db.get(UploadedFile, UUID(file_id_str))
            if file_record:
                file_record.file_category = "activity_participant_import"
                file_record.file_role = "source"
                if file_record.activity_report_id is None:
                    file_record.activity_report_id = activity_id
        except Exception:
            pass

    # Mark proposal as applied
    from datetime import datetime, timezone
    proposal.status = "applied"
    proposal.confirmed_at = datetime.now(timezone.utc)
    proposal.applied_at = datetime.now(timezone.utc)
    proposal.preview_json = {
        **(proposal.preview_json or {}),
        "applied_result": {
            "created_participants": created_participants,
            "updated_participants": updated_participants,
            "already_participants": already_participants,
            "external_participants": external_participants,
            "ignored_rows": ignored_rows,
            "created_members": created_members,
        },
    }

    db.commit()

    return ImportConfirmResult(
        ok=True,
        activity_id=str(activity_id),
        created_participants=created_participants,
        updated_participants=updated_participants,
        already_participants=already_participants,
        external_participants=external_participants,
        ignored_rows=ignored_rows,
        created_members=created_members,
    )


def cancel_participant_import(db: Session, action_id: UUID) -> None:
    """Cancel a pending participant import proposal."""
    from app.models.assistant_action import AssistantActionProposal
    from datetime import datetime, timezone

    proposal = db.get(AssistantActionProposal, action_id)
    if not proposal:
        raise ValueError(f"Action proposal not found: {action_id}")
    if proposal.status != "pending":
        raise ValueError(f"Action proposal is not pending: {proposal.status}")
    proposal.status = "cancelled"
    proposal.cancelled_at = datetime.now(timezone.utc)
    db.commit()
