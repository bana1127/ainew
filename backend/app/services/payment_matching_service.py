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
) -> PaymentMatchingPreview:
    """
    Preview payment matching results WITHOUT modifying the database.
    """
    membership_fee, default_period, _, _ = _get_settings(db)
    if required_amount is None:
        required_amount = membership_fee

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
) -> PaymentMatchingResult:
    """
    Run payment matching and persist results to the database.

    Idempotent: uses upsert pattern on (member_id, period, payment_type).
    """
    membership_fee, _, _, _ = _get_settings(db)
    if required_amount is None:
        required_amount = membership_fee

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
            existing.paid_amount = item.deposit_amount
            existing.status = "paid"
            existing.transaction_id = item.transaction_id
            updated_records += 1
        else:
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
