"""Service for applying manual payment status updates from natural language requests.

Task 23: Handles "박민서 학생이 활동비 15000원을 납부했어" type requests from the
AI assistant, scoped to a specific activity.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

# ── Constants ─────────────────────────────────────────────────────────────────

MEMBER_SUFFIXES = ("학생", "부원", "회원", "님", "씨")

# Korean digit words → int
_KOR_DIGITS: dict[str, int] = {
    "일": 1, "한": 1, "이": 2, "두": 2, "삼": 3, "세": 3,
    "사": 4, "네": 4, "오": 5, "육": 6, "칠": 7, "팔": 8,
    "구": 9, "십": 10, "백": 100, "천": 1000,
}

# Korean digits that can precede 만 (e.g. 이만원, 삼만원)
_KOR_MAN_CHARS = "일이삼사오육칠팔구한두세네"


# ── Data classes ───────────────────────────────────────────────────────────────

@dataclass
class ManualPaymentUpdateResult:
    ok: bool
    requires_confirmation: bool
    member_name: str | None
    payment_type: str
    activity_id: str
    activity_title: str | None
    required_amount: int | None
    previous_paid_amount: int | None
    new_paid_amount: int | None
    previous_status: str | None
    new_status: str | None
    payment_record_id: str | None
    message: str
    candidates: list[dict] | None = None


# ── Parsers ────────────────────────────────────────────────────────────────────

def _normalize(text: str) -> str:
    """Normalize Korean text for fuzzy matching."""
    return unicodedata.normalize("NFC", text).strip()


def extract_member_name(message: str) -> str | None:
    """Extract member name from message, stripping honorific suffixes and particles.

    Two-pass strategy:
    1. Match Korean name (2-4 chars) followed by a known suffix/particle → suffix consumed.
    2. Match Korean name (2-4 chars) at word boundary without suffix.
    """
    _NOISE = {
        # Member role nouns — prevent these from being extracted as names
        "학생", "부원", "회원",
        # Fee / payment nouns
        "활동비", "회비", "납부", "미납", "완료", "상태", "처리", "반영",
        # Action verbs / nouns
        "제출", "입금", "바꿔", "수정", "금액", "만원", "바꿔줘",
        # Review / clarification
        "확인", "부분", "학번", "학과", "전화", "연락", "이름",
    }

    # Korean grammatical particles commonly attached to names (e.g., 박민서가)
    # Longer forms listed first so alternation matches them before shorter ones
    _PARTICLES = ("이가", "이는", "이를", "가", "이", "은", "는", "의", "을", "를")

    suffix_pat = "|".join((*MEMBER_SUFFIXES, *_PARTICLES))

    # Pass 1: name immediately followed by suffix or particle (suffix consumed)
    p1 = re.compile(rf'([가-힣]{{2,4}})(?:{suffix_pat})')
    for m in p1.finditer(message):
        candidate = m.group(1)
        if candidate not in _NOISE:
            return candidate

    # Pass 2: bare Korean name followed by space / end
    p2 = re.compile(r'([가-힣]{2,4})(?=\s|$)')
    for m in p2.finditer(message):
        candidate = m.group(1)
        if candidate not in _NOISE:
            return candidate

    return None


def parse_payment_amount(message: str) -> int | None:
    """Parse a Korean-style monetary amount from message text.

    Supports:
        25000원, 25,000원
        2만5천원, 2만오천원
        이만오천원 (full Korean numerals)
        이만원, 삼만원 (Korean digit + 만)
        만원, 만오천원, 1만5천원
    """
    msg = message.replace(",", "").replace(" ", "")

    # ── 1. Digit + 만 + digit + 천원 (e.g., 1만5천원) ──────────────────────
    m = re.search(r'(\d+)만(\d+)천원?', msg)
    if m:
        return int(m.group(1)) * 10000 + int(m.group(2)) * 1000

    # ── 2. Digit + 만 + Korean digit + 천원 (e.g., 1만오천원) ───────────────
    m = re.search(rf'(\d+)만([{_KOR_MAN_CHARS}])천원?', msg)
    if m:
        cheon = _KOR_DIGITS.get(m.group(2), 0)
        return int(m.group(1)) * 10000 + cheon * 1000

    # ── 3. Korean digit + 만 + Korean digit + 천원 (e.g., 이만오천원) ────────
    # Must come BEFORE the bare 만[kor]천 pattern to prevent partial match
    m = re.search(rf'([{_KOR_MAN_CHARS}])만([{_KOR_MAN_CHARS}])천원?', msg)
    if m:
        man_n = _KOR_DIGITS.get(m.group(1), 0)
        cheon_n = _KOR_DIGITS.get(m.group(2), 0)
        if man_n > 0:
            return man_n * 10000 + cheon_n * 1000

    # ── 4. 만 + Korean chars + 천원 (e.g., 만오천원)  ──────────────────────
    # Negative lookbehind: must not be preceded by a Korean digit (e.g., 이만)
    m = re.search(rf'(?<![{_KOR_MAN_CHARS}])만([가-힣]+)천원?', msg)
    if m:
        kor = m.group(1)
        cheon_val = sum(_KOR_DIGITS.get(c, 0) for c in kor)
        return 10000 + cheon_val * 1000

    # ── 5. Digit + 만원 (e.g., 2만원) ───────────────────────────────────────
    m = re.search(r'(\d+)만원?', msg)
    if m:
        return int(m.group(1)) * 10000

    # ── 6. Korean digit + 만원 (e.g., 이만원, 삼만원) ───────────────────────
    m = re.search(rf'([{_KOR_MAN_CHARS}])만원', msg)
    if m:
        n = _KOR_DIGITS.get(m.group(1), 0)
        if n > 0:
            return n * 10000

    # ── 7. 만원 alone ────────────────────────────────────────────────────────
    if re.search(r'(?<!\d)만원', msg):
        return 10000

    # ── 8. Plain number + 원 ─────────────────────────────────────────────────
    m = re.search(r'(\d{3,})\s*원?', msg)
    if m:
        val = int(m.group(1))
        if val >= 100:
            return val

    return None


def _recalculate_status(paid: int, required: int, current_status: str) -> str:
    """Recalculate payment status from amounts.

    Manual states (exempt, cancelled, need_check) are preserved unless
    the caller explicitly changes them.
    """
    if current_status in ("exempt", "cancelled"):
        return current_status
    if paid == 0:
        return "unpaid"
    if paid < required:
        return "partial"
    if paid == required:
        return "paid"
    return "overpaid"  # paid > required


# ── Main service function ─────────────────────────────────────────────────────

def apply_manual_payment_update(
    db: Session,
    activity_id: UUID,
    message: str,
    member_name: str | None = None,
    student_id: str | None = None,
    amount: int | None = None,
    payment_type: str = "activity_fee",
    dry_run: bool = False,
) -> ManualPaymentUpdateResult:
    """Find the payment record for a member+activity and update paid_amount/status.

    Parameters
    ----------
    db            Active SQLAlchemy session.
    activity_id   The activity scope (must match current activity).
    message       Raw user message (used for name/amount parsing fallback).
    member_name   Pre-extracted member name (optional; parsed from message if omitted).
    student_id    Pre-extracted student_id for disambiguation (optional).
    amount        Pre-parsed amount in KRW (optional; parsed from message if omitted).
    payment_type  Defaults to "activity_fee".

    Returns
    -------
    ManualPaymentUpdateResult with ok=True on success, requires_confirmation on ambiguity.
    """
    if payment_type != "activity_fee":
        return ManualPaymentUpdateResult(
            ok=False,
            requires_confirmation=True,
            member_name=member_name,
            payment_type=payment_type,
            activity_id=str(activity_id),
            activity_title=None,
            required_amount=None,
            previous_paid_amount=None,
            new_paid_amount=None,
            previous_status=None,
            new_status=None,
            payment_record_id=None,
            message="수동 납부 변경 서비스는 활동비(activity_fee)만 처리합니다. 회비는 Payments 회비 탭에서 처리해 주세요.",
        )

    from app.models.activity import ActivityParticipant, ActivityReport
    from app.models.member import Member
    from app.models.payment import PaymentAdjustmentLog, PaymentRecord

    # 1. Resolve activity
    activity = db.get(ActivityReport, activity_id)
    if not activity or getattr(activity, "deleted_at", None) is not None:
        return ManualPaymentUpdateResult(
            ok=False, requires_confirmation=False,
            member_name=member_name, payment_type=payment_type,
            activity_id=str(activity_id), activity_title=None,
            required_amount=None, previous_paid_amount=None,
            new_paid_amount=None, previous_status=None, new_status=None,
            payment_record_id=None,
            message="활동을 찾을 수 없습니다.",
        )

    activity_title = activity.title

    # 2. Extract member name / amount from message if not provided
    parsed_name = member_name or extract_member_name(message)
    parsed_amount = amount if amount is not None else parse_payment_amount(message)

    if not parsed_name:
        return ManualPaymentUpdateResult(
            ok=False, requires_confirmation=True,
            member_name=None, payment_type=payment_type,
            activity_id=str(activity_id), activity_title=activity_title,
            required_amount=None, previous_paid_amount=None,
            new_paid_amount=None, previous_status=None, new_status=None,
            payment_record_id=None,
            message="어떤 부원의 납부 상태를 변경할지 알 수 없습니다. 이름을 함께 입력해 주세요.",
        )

    # 3. Find members among activity participants FIRST (activity-scoped search)
    participants = list(db.scalars(
        select(ActivityParticipant)
        .where(ActivityParticipant.activity_report_id == activity_id)
    ))
    participant_member_ids = {p.member_id for p in participants}

    name_norm = _normalize(parsed_name)

    # Search within activity participants
    participant_query = select(Member).where(
        and_(
            Member.id.in_(participant_member_ids),
            Member.name == name_norm,
        )
    )
    if student_id:
        participant_query = participant_query.where(Member.student_id == student_id)
    matched_in_activity = list(db.scalars(participant_query))

    if not matched_in_activity:
        # Check if member exists in the whole DB (to give a better error message)
        global_query = select(Member).where(Member.name == name_norm)
        if student_id:
            global_query = global_query.where(Member.student_id == student_id)
        matched_globally = list(db.scalars(global_query))

        if matched_globally:
            return ManualPaymentUpdateResult(
                ok=False, requires_confirmation=True,
                member_name=parsed_name, payment_type=payment_type,
                activity_id=str(activity_id), activity_title=activity_title,
                required_amount=None, previous_paid_amount=None,
                new_paid_amount=None, previous_status=None, new_status=None,
                payment_record_id=None,
                message=(
                    f"'{parsed_name}'님은 현재 활동({activity_title}) 참여자 목록에 없습니다. "
                    "참여자로 추가한 뒤 납부 처리를 다시 요청해 주세요."
                ),
            )
        return ManualPaymentUpdateResult(
            ok=False, requires_confirmation=True,
            member_name=parsed_name, payment_type=payment_type,
            activity_id=str(activity_id), activity_title=activity_title,
            required_amount=None, previous_paid_amount=None,
            new_paid_amount=None, previous_status=None, new_status=None,
            payment_record_id=None,
            message=(
                f"'{parsed_name}'라는 이름의 부원을 현재 활동 참여자에서 찾지 못했습니다. "
                "이름을 정확히 입력하거나 학번을 함께 알려주세요."
            ),
        )

    if len(matched_in_activity) > 1:
        candidates = [
            {"member_id": str(m.id), "name": m.name, "student_id": m.student_id}
            for m in matched_in_activity
        ]
        return ManualPaymentUpdateResult(
            ok=False, requires_confirmation=True,
            member_name=parsed_name, payment_type=payment_type,
            activity_id=str(activity_id), activity_title=activity_title,
            required_amount=None, previous_paid_amount=None,
            new_paid_amount=None, previous_status=None, new_status=None,
            payment_record_id=None,
            message=(
                f"'{parsed_name}'라는 이름의 부원이 {len(matched_in_activity)}명 있습니다. "
                "학번을 함께 입력해 주세요."
            ),
            candidates=candidates,
        )

    target_member = matched_in_activity[0]

    # 4. Find payment record (activity_report_id first, then period fallback)
    record: PaymentRecord | None = db.execute(
        select(PaymentRecord).where(
            and_(
                PaymentRecord.member_id == target_member.id,
                PaymentRecord.activity_report_id == activity_id,
                PaymentRecord.payment_type == payment_type,
            )
        )
    ).scalar_one_or_none()

    if not record:
        # Fallback: period-based lookup (handles records created without activity_report_id)
        period_key = f"act-{str(activity_id)[:8]}"
        record = db.execute(
            select(PaymentRecord).where(
                and_(
                    PaymentRecord.member_id == target_member.id,
                    PaymentRecord.period == period_key,
                    PaymentRecord.payment_type == payment_type,
                )
            )
        ).scalar_one_or_none()

    if not record:
        # Try to infer required_amount from other participants' records for this activity
        inferred_required: int | None = None
        # Look for any activity_fee record for this activity to get the standard amount.
        sample = db.execute(
            select(PaymentRecord).where(
                and_(
                    PaymentRecord.activity_report_id == activity_id,
                    PaymentRecord.payment_type == payment_type,
                )
            ).limit(1)
        ).scalar_one_or_none()
        if not sample:
            period_key = f"act-{str(activity_id)[:8]}"
            sample = db.execute(
                select(PaymentRecord).where(
                    and_(
                        PaymentRecord.period == period_key,
                        PaymentRecord.payment_type == payment_type,
                    )
                ).limit(1)
            ).scalar_one_or_none()
        if sample:
            inferred_required = sample.required_amount

        if parsed_amount is None and inferred_required is None:
            return ManualPaymentUpdateResult(
                ok=False, requires_confirmation=True,
                member_name=target_member.name, payment_type=payment_type,
                activity_id=str(activity_id), activity_title=activity_title,
                required_amount=None, previous_paid_amount=None,
                new_paid_amount=None, previous_status=None, new_status=None,
                payment_record_id=None,
                message=(
                    f"'{target_member.name}'님의 {payment_type} 납부 기록이 없습니다. "
                    "활동비 대상 먼저 생성 후 다시 시도해 주세요."
                ),
            )

        # Determine required and paid amounts
        req_amount = inferred_required or parsed_amount or 0
        paid = parsed_amount if parsed_amount is not None else req_amount
        new_status = _recalculate_status(paid, req_amount, "unpaid")

        period_key = f"act-{str(activity_id)[:8]}"
        if dry_run:
            return ManualPaymentUpdateResult(
                ok=True, requires_confirmation=False,
                member_name=target_member.name, payment_type=payment_type,
                activity_id=str(activity_id), activity_title=activity_title,
                required_amount=req_amount, previous_paid_amount=0,
                new_paid_amount=paid, previous_status=None, new_status=new_status,
                payment_record_id=None,
                message=f"'{target_member.name}'님 활동비 납부 기록 생성 및 {paid:,}원 납부 반영 예정입니다.",
            )

        record = PaymentRecord(
            member_id=target_member.id,
            period=period_key,
            payment_type=payment_type,
            required_amount=req_amount,
            paid_amount=paid,
            status=new_status,
            activity_report_id=activity_id,
        )
        db.add(record)
        db.flush()
        db.refresh(record)

        _log(db, record.id, "manual_create_and_pay", None, new_status, 0, paid, message,
             target_member.name, parsed_amount)
        db.commit()

        return ManualPaymentUpdateResult(
            ok=True, requires_confirmation=False,
            member_name=target_member.name, payment_type=payment_type,
            activity_id=str(activity_id), activity_title=activity_title,
            required_amount=req_amount, previous_paid_amount=0,
            new_paid_amount=paid, previous_status=None, new_status=new_status,
            payment_record_id=str(record.id),
            message=f"'{target_member.name}'님 활동비 납부 기록을 생성하고 {paid:,}원 납부 → {new_status}로 반영했습니다.",
        )

    # 5. Apply update to existing record
    prev_status = record.status
    prev_paid = record.paid_amount
    required = record.required_amount

    # If no amount given → treat as full payment (납부 완료)
    new_paid = parsed_amount if parsed_amount is not None else required
    new_status = _recalculate_status(new_paid, required, prev_status)

    if dry_run:
        return ManualPaymentUpdateResult(
            ok=True, requires_confirmation=False,
            member_name=target_member.name, payment_type=payment_type,
            activity_id=str(activity_id), activity_title=activity_title,
            required_amount=required, previous_paid_amount=prev_paid,
            new_paid_amount=new_paid, previous_status=prev_status, new_status=new_status,
            payment_record_id=str(record.id),
            message=f"'{target_member.name}'님의 활동비를 {new_paid:,}원 납부로 반영할 예정입니다.",
        )

    record.paid_amount = new_paid
    record.status = new_status
    record.updated_at = datetime.now(timezone.utc)

    # 6. Log
    _log(db, record.id, "manual_payment_mark",
         prev_status, new_status, prev_paid, new_paid, message,
         target_member.name, parsed_amount)

    db.commit()

    status_label = {
        "paid": "납부 완료", "partial": "부분 납부",
        "overpaid": "오납", "unpaid": "미납",
    }.get(new_status, new_status)
    msg = f"'{target_member.name}'님의 활동비를 {new_paid:,}원 납부 → {status_label}로 반영했습니다."

    return ManualPaymentUpdateResult(
        ok=True, requires_confirmation=False,
        member_name=target_member.name, payment_type=payment_type,
        activity_id=str(activity_id), activity_title=activity_title,
        required_amount=required, previous_paid_amount=prev_paid,
        new_paid_amount=new_paid, previous_status=prev_status, new_status=new_status,
        payment_record_id=str(record.id),
        message=msg,
    )


def _log(
    db: Session,
    record_id: UUID,
    action: str,
    prev_status: str | None,
    new_status: str | None,
    prev_paid: int,
    new_paid: int,
    raw_request: str,
    parsed_member_name: str,
    parsed_amount: int | None,
) -> None:
    from app.models.payment import PaymentAdjustmentLog
    log = PaymentAdjustmentLog(
        payment_record_id=record_id,
        action=action,
        previous_status=prev_status,
        new_status=new_status,
        previous_paid_amount=prev_paid,
        new_paid_amount=new_paid,
        reason=raw_request[:500] if raw_request else None,
        metadata_json={
            "source": "assistant",
            "raw_request": raw_request[:300] if raw_request else None,
            "parsed_member_name": parsed_member_name,
            "parsed_amount": parsed_amount,
        },
    )
    db.add(log)
