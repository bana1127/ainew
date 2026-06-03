from __future__ import annotations

import re
import difflib
from dataclasses import dataclass, field
from datetime import date, datetime
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.orm import Session

from app.models import BankTransaction, Member, PaymentRecord
from app.models.setting import AppSetting


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EXCLUDED_KEYWORDS = [
    "예금이자", "이자", "환불", "네이버페이환불", "결제취소", "취소", "캐시백", "정산"
]

EXCLUDED_KEYWORD_PAYMENT_TYPES: dict[str, str] = {
    "예금이자": "interest",
    "이자": "interest",
    "환불": "refund",
    "네이버페이환불": "refund",
    "결제취소": "refund",
    "취소": "refund",
    "캐시백": "other",
    "정산": "other",
}

STRIP_PREFIXES = [
    "토스", "카카오페이", "메모아", "메모", "입금", "회비", "활동비",
    "KB", "신한", "하나", "우리", "국민",
]

STRIP_TRAILING = ["회비", "활동비", "납부", "이체"]


# ---------------------------------------------------------------------------
# Internal data classes
# ---------------------------------------------------------------------------

@dataclass
class TransactionMatchItem:
    transaction_id: UUID
    transaction_datetime: datetime | None
    memo: str | None
    deposit_amount: int
    matched_member_id: UUID | None
    matched_member_name: str | None
    payment_type: str | None
    match_status: str
    score: float | None
    reason: str | None
    activity_id: UUID | None = None
    activity_title: str | None = None
    match_mode: str | None = None
    expected_amount: int | None = None
    amount_difference: int | None = None
    amount_status: str | None = None
    auto_match: bool = False
    fee_tier: str | None = None


@dataclass
class MemberSummary:
    member_id: UUID
    name: str
    student_id: str | None
    department: str | None
    required_amount: int
    paid_amount: int
    status: str


@dataclass
class PaymentMatchingPreview:
    period: str
    payment_type: str
    required_amount: int
    total_active_members: int
    total_deposit_transactions: int
    matched_count: int
    need_check_count: int
    excluded_count: int
    unpaid_count: int
    matched_items: list[TransactionMatchItem]
    need_check_items: list[TransactionMatchItem]
    excluded_items: list[TransactionMatchItem]
    unpaid_members: list[MemberSummary]


@dataclass
class PaymentMatchingResult:
    period: str
    payment_type: str
    required_amount: int
    total_active_members: int
    total_deposit_transactions: int
    matched_count: int
    need_check_count: int
    excluded_count: int
    unpaid_count: int
    matched_items: list[TransactionMatchItem]
    need_check_items: list[TransactionMatchItem]
    excluded_items: list[TransactionMatchItem]
    unpaid_members: list[MemberSummary]
    created_payment_records: int = 0
    updated_payment_records: int = 0
    updated_transactions: int = 0


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def normalize_memo(memo: str) -> str:
    """Normalize a bank transaction memo for name matching."""
    # 1. Strip whitespace
    result = memo.strip()

    # 2. Remove parenthesized long descriptions (4+ chars inside parens)
    result = re.sub(r'\([^)]{4,}\)', '', result)

    # 3. Replace special chars with space (keep Korean, alphanumeric, whitespace)
    result = re.sub(r'[^가-힣a-zA-Z0-9\s]', ' ', result)

    # 4. Strip known prefixes from the start (repeat until no more matches)
    changed = True
    while changed:
        changed = False
        stripped = result.strip()
        for prefix in STRIP_PREFIXES:
            if stripped.startswith(prefix):
                stripped = stripped[len(prefix):].strip()
                changed = True
        result = stripped

    # 5. Strip trailing keywords
    changed = True
    while changed:
        changed = False
        stripped = result.strip()
        for kw in STRIP_TRAILING:
            if stripped.endswith(kw):
                stripped = stripped[: -len(kw)].strip()
                changed = True
        result = stripped

    # 6. Collapse spaces, strip
    result = re.sub(r'\s+', ' ', result).strip()
    return result


def extract_name_candidates(memo: str) -> list[str]:
    """Extract Korean name candidates (2-4 chars) from normalized memo."""
    normalized = normalize_memo(memo)
    # Find all contiguous Korean word segments
    korean_words = re.findall(r'[가-힣]+', normalized)
    seen: set[str] = set()
    candidates: list[str] = []
    for word in korean_words:
        # A single Korean word segment may itself be a name, or we can try substrings
        # Return unique candidates that are 2-4 chars long
        for length in range(2, 5):
            for start in range(len(word) - length + 1):
                candidate = word[start: start + length]
                if candidate not in seen:
                    seen.add(candidate)
                    candidates.append(candidate)
    return candidates


def is_excluded_transaction(
    memo: str | None, transaction_type: str | None
) -> tuple[bool, str]:
    """
    Determine whether a transaction should be excluded from payment matching.

    Returns (True, payment_type_str) if excluded, else (False, "").
    """
    if memo:
        memo_stripped = memo.strip()
        for keyword in EXCLUDED_KEYWORDS:
            if keyword in memo_stripped:
                payment_type_str = EXCLUDED_KEYWORD_PAYMENT_TYPES.get(keyword, "other")
                return True, payment_type_str
    return False, ""


def calculate_match_score(candidate: str, member_name: str) -> float:
    """
    Calculate similarity score between a name candidate and a member name.

    Uses difflib.SequenceMatcher. Also gives 0.9 for substring containment.
    Returns the maximum score found.
    """
    ratio = difflib.SequenceMatcher(None, candidate, member_name).ratio()
    # Substring bonus
    if candidate in member_name or member_name in candidate:
        ratio = max(ratio, 0.9)
    return ratio


def match_member_from_memo(
    memo: str | None,
    student_id_map: dict[str, "Member"],
    members: list["Member"],
    threshold: float,
) -> tuple["Member | None", float, str, str]:
    """
    Attempt to match a bank transaction memo to a member.

    Returns (matched_member, score, match_status, reason).
    match_status is one of: "matched", "need_check", "unmatched".
    """
    # 1. No memo
    if not memo or not memo.strip():
        return None, 0.0, "unmatched", "적요 없음"

    memo_stripped = memo.strip()

    # 2. Student ID match — if any member's student_id appears verbatim in memo
    for sid, member in student_id_map.items():
        if sid and sid in memo_stripped:
            return member, 1.0, "matched", f"학번 일치: {sid}"

    normalized = normalize_memo(memo_stripped)
    normalized_no_space = normalized.replace(" ", "")

    # 3. Exact name match: member.name in normalized_memo
    for member in members:
        if member.name and member.name in normalized:
            return member, 1.0, "matched", f"이름 정확 일치: {member.name}"

    # 4. Normalized (no-space) match
    for member in members:
        if member.name:
            name_no_space = member.name.replace(" ", "")
            if name_no_space and name_no_space in normalized_no_space:
                return member, 0.95, "matched", f"이름 공백제거 일치: {member.name}"

    # 5. Difflib similarity on name candidates
    candidates = extract_name_candidates(memo_stripped)
    if not candidates:
        return None, 0.0, "unmatched", "이름 후보 없음"

    scored: list[tuple[float, "Member"]] = []
    seen_member_ids: set = set()

    for candidate in candidates:
        for member in members:
            if not member.name:
                continue
            score = calculate_match_score(candidate, member.name)
            if score >= threshold:
                # Keep the best score per member
                existing = next(
                    (s for s, m in scored if m.id == member.id), None
                )
                if existing is None:
                    scored.append((score, member))
                else:
                    # Update if better
                    scored = [
                        (max(s, score), m) if m.id == member.id else (s, m)
                        for s, m in scored
                    ]

    if not scored:
        return None, 0.0, "unmatched", "유사한 이름 없음"

    # Sort by score descending
    scored.sort(key=lambda x: x[0], reverse=True)

    if len(scored) == 1:
        score, member = scored[0]
        return member, score, "matched", f"유사도 매칭: {member.name} ({score:.2f})"

    # Multiple candidates above threshold -> need_check
    best_score, best_member = scored[0]
    candidate_names = ", ".join(m.name for _, m in scored[:5])
    return (
        best_member,
        best_score,
        "need_check",
        f"복수 후보 ({len(scored)}명): {candidate_names}",
    )


# ---------------------------------------------------------------------------
# Main functions
# ---------------------------------------------------------------------------

def _get_settings(db: Session) -> tuple[int, str, float, list[int]]:
    """
    Read matching configuration from app_settings.

    Returns (membership_fee, default_period, threshold, activity_fee_amounts).
    """
    membership_fee = 30000
    default_period = "2026-1"
    threshold = 0.8
    activity_fee_amounts: list[int] = []

    rows = db.execute(select(AppSetting)).scalars().all()
    setting_map: dict[str, object] = {row.key: row.value for row in rows}

    # membership_fee_amount
    mfa = setting_map.get("membership_fee_amount")
    if isinstance(mfa, dict) and "amount" in mfa:
        try:
            membership_fee = int(mfa["amount"])
        except (ValueError, TypeError):
            pass

    # default_payment_period
    dpp = setting_map.get("default_payment_period")
    if isinstance(dpp, dict) and "period" in dpp:
        default_period = str(dpp["period"])

    # transaction_matching_threshold
    tmt = setting_map.get("transaction_matching_threshold")
    if isinstance(tmt, dict) and "score" in tmt:
        try:
            threshold = float(tmt["score"])
        except (ValueError, TypeError):
            pass

    # activity_fee_amounts
    afa = setting_map.get("activity_fee_amounts")
    if isinstance(afa, dict) and "amounts" in afa:
        raw_amounts = afa["amounts"]
        if isinstance(raw_amounts, list):
            try:
                activity_fee_amounts = [int(a) for a in raw_amounts]
            except (ValueError, TypeError):
                pass

    return membership_fee, default_period, threshold, activity_fee_amounts


def classify_transaction(
    deposit_amount: int,
    membership_fee: int,
    activity_fee_amounts: list[int],
) -> str:
    """Classify a deposit transaction by its amount."""
    if deposit_amount == membership_fee:
        return "membership_fee"
    elif deposit_amount in activity_fee_amounts:
        return "activity_fee"
    else:
        return "other"


def evaluate_membership_fee_match_gate(
    *,
    deposit_amount: int,
    required_amount: int | None,
    has_payment_record: bool,
    record_status: str | None,
    existing_paid_amount: int,
    name_status: str,
    transaction_already_matched: bool = False,
) -> tuple[str, str, bool]:
    """Return (match_status, amount_status, auto_match) for membership fees.

    Membership fee auto matching is intentionally strict: a transaction may be
    auto-applied only when the member already has a PaymentRecord, the record is
    unsettled, and deposit_amount exactly equals that record's required_amount.
    """
    if transaction_already_matched:
        return "need_check", "already_matched", False
    if not has_payment_record or required_amount is None:
        return "need_check", "missing_payment_record", False
    if record_status in ("paid", "exempt") or existing_paid_amount > 0:
        return "need_check", "already_paid", False
    if required_amount <= 0:
        return "need_check", "amount_mismatch_overpaid", False
    if deposit_amount < required_amount:
        return "need_check", "amount_mismatch_partial", False
    if deposit_amount > required_amount:
        return "need_check", "amount_mismatch_overpaid", False
    if name_status != "matched":
        return "need_check", "name_check_required", False
    return "matched", "exact_amount", True


def _membership_fee_reason(amount_status: str, member_name: str | None = None) -> str:
    name = f"{member_name} " if member_name else ""
    reasons = {
        "exact_amount": f"{name}회비 필요 금액과 입금액이 정확히 일치",
        "amount_mismatch_partial": f"{name}회비 금액 불일치: 부분 납부 후보",
        "amount_mismatch_overpaid": f"{name}회비 금액 불일치: 초과 입금 또는 임원 입금 확인 필요",
        "amount_mismatch": f"{name}회비 금액 불일치",
        "missing_payment_record": f"{name}회비 PaymentRecord가 없어 자동 매칭 불가",
        "already_paid": f"{name}이미 납부 완료 또는 납부 금액이 있어 확인 필요",
        "already_matched": "이미 다른 납부 기록에 연결된 거래내역",
        "name_check_required": "금액은 일치하지만 납부자 이름 확인 필요",
    }
    return reasons.get(amount_status, amount_status)


def _score_activity_fee_transaction(
    memo: str | None,
    deposit_amount: int,
    member: Member,
    payment_record: PaymentRecord,
    activity_title: str | None,
) -> float:
    """Score a transaction against an activity_fee payment record."""
    score = 0.0
    if not memo:
        return score

    memo_norm = normalize_memo(memo)
    memo_stripped = memo.strip()

    # Student ID match — strongest signal
    if member.student_id and member.student_id in memo_stripped:
        score += 4.0

    # Name match
    if member.name and member.name in memo_norm:
        score += 3.0
    elif member.name:
        ratio = difflib.SequenceMatcher(None, member.name, memo_norm).ratio()
        if ratio >= 0.8:
            score += 2.0

    # Amount match
    if payment_record.required_amount > 0 and deposit_amount == payment_record.required_amount:
        score += 2.0

    # Activity title in memo
    if activity_title:
        # Try partial title match
        short_title = activity_title[:4] if len(activity_title) >= 4 else activity_title
        if short_title and short_title in memo_stripped:
            score += 1.0

    return score


def _run_activity_fee_matching(
    db: Session,
    activity_id: UUID,
    start_date: date | None,
    end_date: date | None,
) -> tuple[
    list[TransactionMatchItem],
    list[TransactionMatchItem],
    list[TransactionMatchItem],
    list[Member],
]:
    """Match transactions against activity_fee payment records for a specific activity."""
    from app.models.activity import ActivityReport  # lazy import to avoid test stub issues

    _, _, threshold, _ = _get_settings(db)

    activity = db.get(ActivityReport, activity_id)
    activity_title = activity.title if activity else None
    period_key = f"act-{str(activity_id)[:8]}"

    # Get activity_fee payment records for this activity
    fee_records: list[PaymentRecord] = list(db.scalars(
        select(PaymentRecord).where(
            and_(
                PaymentRecord.period == period_key,
                PaymentRecord.payment_type == "activity_fee",
            )
        )
    ))

    # Build member map from fee records
    member_ids = {r.member_id for r in fee_records}
    members: list[Member] = list(db.scalars(
        select(Member).where(Member.id.in_(member_ids))
    )) if member_ids else []
    member_map: dict[UUID, Member] = {m.id: m for m in members}

    # Get deposit transactions
    query = select(BankTransaction).where(
        and_(
            BankTransaction.deposit_amount > 0,
            BankTransaction.match_status != "excluded",
        )
    )
    if start_date is not None:
        query = query.where(
            BankTransaction.transaction_datetime >= datetime.combine(start_date, datetime.min.time())
        )
    if end_date is not None:
        query = query.where(
            BankTransaction.transaction_datetime <= datetime.combine(end_date, datetime.max.time())
        )
    transactions: list[BankTransaction] = list(db.scalars(query))

    # Filter out already-paid/exempt records from candidates
    unpaid_records = [
        r for r in fee_records
        if r.status not in ("paid", "exempt")
    ]
    unpaid_member_ids = {r.member_id for r in unpaid_records}
    unpaid_members_list = [member_map[mid] for mid in unpaid_member_ids if mid in member_map]

    matched_items: list[TransactionMatchItem] = []
    need_check_items: list[TransactionMatchItem] = []
    excluded_items: list[TransactionMatchItem] = []

    matched_member_ids: set[UUID] = set()

    for txn in transactions:
        memo = txn.memo

        # Check exclusion
        excluded, exc_payment_type = is_excluded_transaction(memo, txn.transaction_type)
        if excluded:
            excluded_items.append(TransactionMatchItem(
                transaction_id=txn.id,
                transaction_datetime=txn.transaction_datetime,
                memo=memo,
                deposit_amount=txn.deposit_amount or 0,
                matched_member_id=None,
                matched_member_name=None,
                payment_type=exc_payment_type,
                match_status="excluded",
                score=None,
                reason="제외 키워드 감지",
                activity_id=activity_id,
                activity_title=activity_title,
                match_mode="selected_activity_fee",
            ))
            continue

        # Score each unpaid fee record
        scored: list[tuple[float, Member, PaymentRecord]] = []
        for rec in unpaid_records:
            member = member_map.get(rec.member_id)
            if not member:
                continue
            s = _score_activity_fee_transaction(
                memo, txn.deposit_amount or 0, member, rec, activity_title
            )
            if s > 0:
                scored.append((s, member, rec))

        if not scored:
            need_check_items.append(TransactionMatchItem(
                transaction_id=txn.id,
                transaction_datetime=txn.transaction_datetime,
                memo=memo,
                deposit_amount=txn.deposit_amount or 0,
                matched_member_id=None,
                matched_member_name=None,
                payment_type="activity_fee",
                match_status="unmatched",
                score=0.0,
                reason="활동비 납부자 불일치",
                activity_id=activity_id,
                activity_title=activity_title,
                match_mode="selected_activity_fee",
                amount_status="name_check_required",
                auto_match=False,
            ))
            continue

        scored.sort(key=lambda x: x[0], reverse=True)
        best_score, best_member, best_rec = scored[0]
        deposit_amount = int(txn.deposit_amount or 0)
        expected_amount = int(best_rec.required_amount or 0)
        amount_difference = deposit_amount - expected_amount
        if deposit_amount != expected_amount:
            amount_status = (
                "amount_mismatch_partial"
                if deposit_amount < expected_amount
                else "amount_mismatch_overpaid"
            )
            need_check_items.append(TransactionMatchItem(
                transaction_id=txn.id,
                transaction_datetime=txn.transaction_datetime,
                memo=memo,
                deposit_amount=deposit_amount,
                matched_member_id=best_member.id,
                matched_member_name=best_member.name,
                payment_type="activity_fee",
                match_status="need_check",
                score=round(best_score, 2),
                reason=f"활동비 금액 불일치: 필요 {expected_amount:,}원 / 입금 {deposit_amount:,}원",
                activity_id=activity_id,
                activity_title=activity_title,
                match_mode="selected_activity_fee",
                expected_amount=expected_amount,
                amount_difference=amount_difference,
                amount_status=amount_status,
                auto_match=False,
            ))
            continue

        if len(scored) == 1 or scored[0][0] > scored[1][0] + 1.0:
            # Clear winner
            matched_items.append(TransactionMatchItem(
                transaction_id=txn.id,
                transaction_datetime=txn.transaction_datetime,
                memo=memo,
                deposit_amount=deposit_amount,
                matched_member_id=best_member.id,
                matched_member_name=best_member.name,
                payment_type="activity_fee",
                match_status="matched",
                score=round(best_score, 2),
                reason=f"활동비 매칭: {best_member.name} (점수 {best_score:.1f})",
                activity_id=activity_id,
                activity_title=activity_title,
                match_mode="selected_activity_fee",
                expected_amount=expected_amount,
                amount_difference=amount_difference,
                amount_status="exact_amount",
                auto_match=True,
            ))
            matched_member_ids.add(best_member.id)
        else:
            candidates_str = ", ".join(m.name for _, m, _ in scored[:3])
            need_check_items.append(TransactionMatchItem(
                transaction_id=txn.id,
                transaction_datetime=txn.transaction_datetime,
                memo=memo,
                deposit_amount=deposit_amount,
                matched_member_id=best_member.id,
                matched_member_name=best_member.name,
                payment_type="activity_fee",
                match_status="need_check",
                score=round(best_score, 2),
                reason=f"복수 후보: {candidates_str}",
                activity_id=activity_id,
                activity_title=activity_title,
                match_mode="selected_activity_fee",
                expected_amount=expected_amount,
                amount_difference=amount_difference,
                amount_status="name_check_required",
                auto_match=False,
            ))

    unpaid_fee_members: list[Member] = [
        m for m in unpaid_members_list if m.id not in matched_member_ids
    ]
    return matched_items, need_check_items, excluded_items, unpaid_fee_members


def _run_matching(
    db: Session,
    period: str,
    payment_type: str,
    required_amount: int,
    start_date: date | None,
    end_date: date | None,
) -> tuple[
    list[TransactionMatchItem],
    list[TransactionMatchItem],
    list[TransactionMatchItem],
    list[Member],
]:
    """
    Core matching logic shared by preview and apply.

    Returns (matched_items, need_check_items, excluded_items, unpaid_members).
    """
    membership_fee, _, threshold, activity_fee_amounts = _get_settings(db)

    # 1. Get active members
    active_members: list[Member] = (
        db.execute(select(Member).where(Member.status == "active"))
        .scalars()
        .all()
    )

    # 2. Get deposit transactions
    query = select(BankTransaction).where(
        and_(
            BankTransaction.deposit_amount > 0,
            BankTransaction.match_status != "excluded",
        )
    )
    if start_date is not None:
        query = query.where(BankTransaction.transaction_datetime >= datetime.combine(start_date, datetime.min.time()))
    if end_date is not None:
        query = query.where(BankTransaction.transaction_datetime <= datetime.combine(end_date, datetime.max.time()))

    transactions: list[BankTransaction] = db.execute(query).scalars().all()

    # 3. Build student_id_map
    student_id_map: dict[str, Member] = {}
    for member in active_members:
        if member.student_id:
            student_id_map[member.student_id] = member

    membership_record_map: dict[UUID, PaymentRecord] = {}
    linked_transaction_ids: set[UUID] = set()
    if payment_type == "membership_fee":
        member_ids = {m.id for m in active_members}
        if member_ids:
            membership_records = list(db.scalars(
                select(PaymentRecord).where(
                    and_(
                        PaymentRecord.period == period,
                        PaymentRecord.payment_type == "membership_fee",
                        PaymentRecord.member_id.in_(member_ids),
                    )
                )
            ))
            membership_record_map = {r.member_id: r for r in membership_records}
            linked_transaction_ids = {
                r.transaction_id for r in membership_records if r.transaction_id is not None
            }

    matched_items: list[TransactionMatchItem] = []
    need_check_items: list[TransactionMatchItem] = []
    excluded_items: list[TransactionMatchItem] = []

    matched_member_ids: set = set()

    # 4. Process each transaction
    for txn in transactions:
        memo = txn.memo

        # 4a. Check exclusion
        excluded, exc_payment_type = is_excluded_transaction(memo, txn.transaction_type)
        if excluded:
            item = TransactionMatchItem(
                transaction_id=txn.id,
                transaction_datetime=txn.transaction_datetime,
                memo=memo,
                deposit_amount=txn.deposit_amount or 0,
                matched_member_id=None,
                matched_member_name=None,
                payment_type=exc_payment_type,
                match_status="excluded",
                score=None,
                reason="제외 키워드 감지",
            )
            excluded_items.append(item)
            continue

        # 4b. Match member from memo
        matched_member, score, match_status, reason = match_member_from_memo(
            memo, student_id_map, active_members, threshold
        )

        if payment_type == "membership_fee":
            deposit_amount = int(txn.deposit_amount or 0)
            transaction_already_matched = txn.id in linked_transaction_ids
            if matched_member:
                fee_record = membership_record_map.get(matched_member.id)
                required_for_member = int(fee_record.required_amount) if fee_record else None
                status, amount_status, auto_match = evaluate_membership_fee_match_gate(
                    deposit_amount=deposit_amount,
                    required_amount=required_for_member,
                    has_payment_record=fee_record is not None,
                    record_status=getattr(fee_record, "status", None) if fee_record else None,
                    existing_paid_amount=int(getattr(fee_record, "paid_amount", 0) or 0) if fee_record else 0,
                    name_status=match_status,
                    transaction_already_matched=transaction_already_matched,
                )
                item = TransactionMatchItem(
                    transaction_id=txn.id,
                    transaction_datetime=txn.transaction_datetime,
                    memo=memo,
                    deposit_amount=deposit_amount,
                    matched_member_id=matched_member.id,
                    matched_member_name=matched_member.name,
                    payment_type="membership_fee",
                    match_status=status,
                    score=score,
                    reason=_membership_fee_reason(amount_status, matched_member.name),
                    expected_amount=required_for_member,
                    amount_difference=deposit_amount - required_for_member if required_for_member is not None else None,
                    amount_status=amount_status,
                    auto_match=auto_match,
                    fee_tier=getattr(fee_record, "fee_tier", None) if fee_record else None,
                )
                if auto_match:
                    matched_items.append(item)
                    matched_member_ids.add(matched_member.id)
                else:
                    need_check_items.append(item)
                continue

            exact_amount_candidates = [
                (m, r) for m in active_members
                if (r := membership_record_map.get(m.id)) is not None
                and r.status not in ("paid", "exempt")
                and int(r.paid_amount or 0) == 0
                and int(r.required_amount or 0) == deposit_amount
            ]
            if exact_amount_candidates:
                candidate_member, candidate_record = exact_amount_candidates[0]
                amount_status = "name_check_required"
                need_check_items.append(TransactionMatchItem(
                    transaction_id=txn.id,
                    transaction_datetime=txn.transaction_datetime,
                    memo=memo,
                    deposit_amount=deposit_amount,
                    matched_member_id=candidate_member.id,
                    matched_member_name=candidate_member.name,
                    payment_type="membership_fee",
                    match_status="need_check",
                    score=score if score else None,
                    reason=_membership_fee_reason(amount_status, candidate_member.name),
                    expected_amount=int(candidate_record.required_amount or 0),
                    amount_difference=deposit_amount - int(candidate_record.required_amount or 0),
                    amount_status=amount_status,
                    auto_match=False,
                    fee_tier=getattr(candidate_record, "fee_tier", None),
                ))
                continue

        # Determine payment_type for this transaction
        detected_payment_type = classify_transaction(
            txn.deposit_amount or 0, membership_fee, activity_fee_amounts
        )
        # If a specific payment_type was requested, use it for matched records
        effective_payment_type = payment_type if matched_member else detected_payment_type

        item = TransactionMatchItem(
            transaction_id=txn.id,
            transaction_datetime=txn.transaction_datetime,
            memo=memo,
            deposit_amount=txn.deposit_amount or 0,
            matched_member_id=matched_member.id if matched_member else None,
            matched_member_name=matched_member.name if matched_member else None,
            payment_type=effective_payment_type,
            match_status=match_status,
            score=score,
            reason=reason,
        )

        if match_status == "matched":
            matched_items.append(item)
            if matched_member:
                matched_member_ids.add(matched_member.id)
        elif match_status == "need_check":
            need_check_items.append(item)
            # Do NOT add to matched_member_ids; treated as unpaid until confirmed
        else:
            # unmatched
            matched_items_status_unmatched = TransactionMatchItem(
                transaction_id=txn.id,
                transaction_datetime=txn.transaction_datetime,
                memo=memo,
                deposit_amount=txn.deposit_amount or 0,
                matched_member_id=None,
                matched_member_name=None,
                payment_type=detected_payment_type,
                match_status="unmatched",
                score=score if score else None,
                reason=reason,
            )
            # Unmatched transactions are not added to any result list for preview
            # but we still need to record them — add to need_check to surface them
            # Actually per spec, only matched / need_check / excluded are returned.
            # Unmatched are implicitly "transactions without a home" — they don't
            # appear in matched or need_check explicitly. We'll put them in
            # need_check_items so they're visible.
            need_check_items.append(matched_items_status_unmatched)

    # 5. Unpaid members = active members not in matched set
    unpaid_members: list[Member] = [
        m for m in active_members if m.id not in matched_member_ids
    ]

    return matched_items, need_check_items, excluded_items, unpaid_members


def preview_payment_matching(
    db: Session,
    period: str,
    payment_type: str = "membership_fee",
    required_amount: int | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    match_mode: str = "auto",
    activity_id: UUID | None = None,
) -> PaymentMatchingPreview:
    """
    Preview payment matching results WITHOUT modifying the database.
    """
    membership_fee, default_period, _, _ = _get_settings(db)
    if required_amount is None:
        required_amount = membership_fee

    if match_mode == "selected_activity_fee" and activity_id:
        matched_items, need_check_items, excluded_items, unpaid_members = _run_activity_fee_matching(
            db, activity_id, start_date, end_date
        )
        payment_type = "activity_fee"
    else:
        matched_items, need_check_items, excluded_items, unpaid_members = _run_matching(
            db, period, payment_type, required_amount, start_date, end_date
        )

    # Count total active members
    total_active = db.execute(
        select(Member).where(Member.status == "active")
    ).scalars().all()

    # Count deposit transactions queried (re-query for count)
    txn_query = select(BankTransaction).where(
        and_(
            BankTransaction.deposit_amount > 0,
            BankTransaction.match_status != "excluded",
        )
    )
    if start_date is not None:
        txn_query = txn_query.where(
            BankTransaction.transaction_datetime >= datetime.combine(start_date, datetime.min.time())
        )
    if end_date is not None:
        txn_query = txn_query.where(
            BankTransaction.transaction_datetime <= datetime.combine(end_date, datetime.max.time())
        )
    total_transactions = len(db.execute(txn_query).scalars().all())

    unpaid_summaries = [
        MemberSummary(
            member_id=m.id,
            name=m.name,
            student_id=m.student_id,
            department=m.department,
            required_amount=required_amount,
            paid_amount=0,
            status="unpaid",
        )
        for m in unpaid_members
    ]

    return PaymentMatchingPreview(
        period=period,
        payment_type=payment_type,
        required_amount=required_amount,
        total_active_members=len(total_active),
        total_deposit_transactions=total_transactions,
        matched_count=len(matched_items),
        need_check_count=len(need_check_items),
        excluded_count=len(excluded_items),
        unpaid_count=len(unpaid_summaries),
        matched_items=matched_items,
        need_check_items=need_check_items,
        excluded_items=excluded_items,
        unpaid_members=unpaid_summaries,
    )


def apply_payment_matching(
    db: Session,
    period: str,
    payment_type: str = "membership_fee",
    required_amount: int | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    match_mode: str = "auto",
    activity_id: UUID | None = None,
) -> PaymentMatchingResult:
    """
    Run payment matching and persist results to the database.

    Idempotent: uses upsert pattern on (member_id, period, payment_type).
    """
    membership_fee, _, _, _ = _get_settings(db)
    if required_amount is None:
        required_amount = membership_fee

    if match_mode == "selected_activity_fee" and activity_id:
        matched_items, need_check_items, excluded_items, unpaid_members = _run_activity_fee_matching(
            db, activity_id, start_date, end_date
        )
        payment_type = "activity_fee"
        # Use the activity's period_key for records
        period = f"act-{str(activity_id)[:8]}"
    else:
        matched_items, need_check_items, excluded_items, unpaid_members = _run_matching(
            db, period, payment_type, required_amount, start_date, end_date
        )

    # Count totals for result
    total_active = db.execute(
        select(Member).where(Member.status == "active")
    ).scalars().all()

    txn_query = select(BankTransaction).where(
        and_(
            BankTransaction.deposit_amount > 0,
            BankTransaction.match_status != "excluded",
        )
    )
    if start_date is not None:
        txn_query = txn_query.where(
            BankTransaction.transaction_datetime >= datetime.combine(start_date, datetime.min.time())
        )
    if end_date is not None:
        txn_query = txn_query.where(
            BankTransaction.transaction_datetime <= datetime.combine(end_date, datetime.max.time())
        )
    total_transactions = len(db.execute(txn_query).scalars().all())

    created_records = 0
    updated_records = 0
    updated_transactions = 0

    # 2. Update matched bank_transactions
    for item in matched_items:
        if item.match_status != "matched":
            continue
        txn = db.get(BankTransaction, item.transaction_id)
        if txn is not None:
            txn.matched_member_id = item.matched_member_id
            txn.payment_type = item.payment_type
            txn.match_status = "matched"
            updated_transactions += 1

    # 3. Update need_check bank_transactions
    for item in need_check_items:
        txn = db.get(BankTransaction, item.transaction_id)
        if txn is not None:
            if item.matched_member_id:
                txn.matched_member_id = item.matched_member_id
            txn.match_status = item.match_status  # "need_check" or "unmatched"
            updated_transactions += 1

    # 4. Update excluded bank_transactions
    for item in excluded_items:
        txn = db.get(BankTransaction, item.transaction_id)
        if txn is not None:
            txn.match_status = "excluded"
            txn.payment_type = item.payment_type
            updated_transactions += 1

    # 5. Upsert payment_records for matched members (paid)
    for item in matched_items:
        if item.match_status != "matched" or item.matched_member_id is None:
            continue

        existing = db.execute(
            select(PaymentRecord).where(
                and_(
                    PaymentRecord.member_id == item.matched_member_id,
                    PaymentRecord.period == period,
                    PaymentRecord.payment_type == payment_type,
                )
            )
        ).scalar_one_or_none()

        if existing is not None:
            if payment_type == "membership_fee":
                if (
                    existing.status in ("paid", "exempt")
                    or int(existing.paid_amount or 0) > 0
                    or item.deposit_amount != int(existing.required_amount or 0)
                ):
                    continue
            existing.paid_amount = item.deposit_amount
            existing.status = "paid"
            existing.transaction_id = item.transaction_id
            updated_records += 1
        else:
            if payment_type == "membership_fee":
                continue
            new_record = PaymentRecord(
                member_id=item.matched_member_id,
                period=period,
                payment_type=payment_type,
                required_amount=required_amount,
                paid_amount=item.deposit_amount,
                status="paid",
                transaction_id=item.transaction_id,
            )
            db.add(new_record)
            created_records += 1

    # 6. Upsert payment_records for unpaid members
    for member in unpaid_members:
        existing = db.execute(
            select(PaymentRecord).where(
                and_(
                    PaymentRecord.member_id == member.id,
                    PaymentRecord.period == period,
                    PaymentRecord.payment_type == payment_type,
                )
            )
        ).scalar_one_or_none()

        if existing is not None:
            # Only update to unpaid if it was not already paid/partial
            if existing.status not in ("paid", "partial", "exempt"):
                existing.status = "unpaid"
                updated_records += 1
        else:
            if payment_type == "membership_fee":
                continue
            new_record = PaymentRecord(
                member_id=member.id,
                period=period,
                payment_type=payment_type,
                required_amount=required_amount,
                paid_amount=0,
                status="unpaid",
                transaction_id=None,
            )
            db.add(new_record)
            created_records += 1

    # 7. Commit
    db.commit()

    # 8. Build result
    unpaid_summaries = [
        MemberSummary(
            member_id=m.id,
            name=m.name,
            student_id=m.student_id,
            department=m.department,
            required_amount=required_amount,
            paid_amount=0,
            status="unpaid",
        )
        for m in unpaid_members
    ]

    return PaymentMatchingResult(
        period=period,
        payment_type=payment_type,
        required_amount=required_amount,
        total_active_members=len(total_active),
        total_deposit_transactions=total_transactions,
        matched_count=len(matched_items),
        need_check_count=len(need_check_items),
        excluded_count=len(excluded_items),
        unpaid_count=len(unpaid_summaries),
        matched_items=matched_items,
        need_check_items=need_check_items,
        excluded_items=excluded_items,
        unpaid_members=unpaid_summaries,
        created_payment_records=created_records,
        updated_payment_records=updated_records,
        updated_transactions=updated_transactions,
    )
