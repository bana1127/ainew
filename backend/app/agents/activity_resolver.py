"""Activity Resolver — determines which activity a request relates to.

Resolves activity context by:
1. Direct activity_id lookup (highest priority)
2. Keyword/text search against existing activities
3. Draft creation if activity keywords present but no match found
4. None if request is unrelated to any activity
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.activity import ActivityReport, ActivityCategory

# Activity-related keywords that indicate a request is about an activity
ACTIVITY_KEYWORDS = {
    "활동", "스터디", "회의", "OT", "행사", "MT", "공모전",
    "세미나", "모임", "교육", "발표", "워크숍", "워크샵",
    "보고서", "사진", "증빙", "영수증", "활동비", "참가비",
    "참여자", "행사비",
}


@dataclass
class ActivityCandidate:
    id: str
    title: str
    activity_date: str | None
    location: str | None
    status: str
    score: float


@dataclass
class ActivityResolutionResult:
    mode: str  # linked | candidate | create_draft | needs_confirmation | none
    activity_id: str | None = None
    activity_title: str | None = None
    confidence: float = 0.0
    candidates: list[ActivityCandidate] = field(default_factory=list)
    draft: dict | None = None
    reason: str = ""


def resolve_activity_context(
    db: Session,
    message: str | None,
    file_names: list[str] | None,
    activity_id: UUID | None,
    activity_mode: str = "auto",
    create_activity_if_missing: bool = False,
) -> ActivityResolutionResult:
    """Determine which activity (if any) this request relates to.

    Priority:
    1. Explicit activity_id — always trusted
    2. activity_mode = none — skip resolution
    3. Message-based search
    4. Draft generation if activity keywords found
    """
    # activity_mode = none → skip
    if activity_mode == "none":
        return ActivityResolutionResult(mode="none", reason="activity_mode=none")

    # Explicit activity_id provided
    if activity_id is not None:
        report = db.get(ActivityReport, activity_id)
        if report:
            return ActivityResolutionResult(
                mode="linked",
                activity_id=str(report.id),
                activity_title=report.title,
                confidence=1.0,
                reason="activity_id explicitly provided",
            )
        else:
            return ActivityResolutionResult(
                mode="needs_confirmation",
                confidence=0.0,
                reason=f"activity_id {activity_id} not found",
            )

    # No text to search — can't resolve
    if not message:
        return ActivityResolutionResult(mode="none", reason="no message provided")

    # activity_mode = create_new → skip search, go straight to draft
    if activity_mode == "create_new":
        draft = _build_draft(message)
        if draft:
            return ActivityResolutionResult(
                mode="create_draft",
                confidence=0.8,
                draft=draft,
                reason="activity_mode=create_new",
            )
        return ActivityResolutionResult(mode="none", reason="activity_mode=create_new but no draft info")

    # Search for existing activity candidates
    candidates = _search_candidates(db, message)

    if candidates:
        best = candidates[0]
        if best.score >= 0.75 and len(candidates) == 1:
            return ActivityResolutionResult(
                mode="linked",
                activity_id=best.id,
                activity_title=best.title,
                confidence=best.score,
                candidates=candidates,
                reason=f"single high-confidence match (score={best.score:.2f})",
            )
        elif best.score >= 0.45 or len(candidates) > 1:
            return ActivityResolutionResult(
                mode="needs_confirmation",
                confidence=best.score,
                candidates=candidates[:5],
                reason=f"multiple candidates or medium confidence (best={best.score:.2f})",
            )

    # No match found — check if request is activity-related
    is_activity_request = _has_activity_keywords(message)
    if is_activity_request and (create_activity_if_missing or activity_mode == "auto"):
        draft = _build_draft(message)
        if draft:
            return ActivityResolutionResult(
                mode="create_draft",
                confidence=0.6,
                draft=draft,
                reason="activity keywords found but no existing match",
            )

    return ActivityResolutionResult(mode="none", reason="no activity context detected")


def _search_candidates(db: Session, message: str) -> list[ActivityCandidate]:
    """Search for activity candidates using SQL LIKE matching."""
    words = _extract_meaningful_words(message)
    if not words:
        return []

    # Build OR conditions for title, location, input_text
    conditions = []
    for word in words[:8]:  # limit to avoid too many conditions
        pattern = f"%{word}%"
        conditions.extend([
            ActivityReport.title.ilike(pattern),
            ActivityReport.location.ilike(pattern),
            ActivityReport.input_text.ilike(pattern),
        ])

    stmt = (
        select(ActivityReport)
        .where(or_(*conditions))
        .where(ActivityReport.status != "archived")
        .order_by(ActivityReport.activity_date.desc().nullslast())
        .limit(10)
    )
    reports = list(db.scalars(stmt))

    # Extract possible date from message
    msg_date = _extract_date(message)

    candidates = []
    for report in reports:
        score = _score_candidate(report, words, msg_date)
        if score >= 0.1:
            candidates.append(ActivityCandidate(
                id=str(report.id),
                title=report.title,
                activity_date=str(report.activity_date) if report.activity_date else None,
                location=report.location,
                status=report.status,
                score=score,
            ))

    candidates.sort(key=lambda c: c.score, reverse=True)
    return candidates


def _score_candidate(report: ActivityReport, words: list[str], msg_date: date | None) -> float:
    """Calculate match score for an activity report."""
    score = 0.0

    title_lower = (report.title or "").lower()
    for word in words:
        if len(word) >= 2 and word.lower() in title_lower:
            score += 0.5
            break

    location_lower = (report.location or "").lower()
    for word in words:
        if len(word) >= 2 and word.lower() in location_lower:
            score += 0.1
            break

    input_lower = (report.input_text or "").lower()
    for word in words:
        if len(word) >= 2 and word.lower() in input_lower:
            score += 0.1
            break

    if msg_date and report.activity_date:
        days_diff = abs((report.activity_date - msg_date).days)
        if days_diff == 0:
            score += 0.2
        elif days_diff <= 3:
            score += 0.1
        elif days_diff <= 7:
            score += 0.05

    # Recency bonus
    if report.activity_date:
        days_since = (date.today() - report.activity_date).days
        if 0 <= days_since <= 30:
            score += 0.1
        elif 0 <= days_since <= 90:
            score += 0.05

    return min(score, 1.0)


def _has_activity_keywords(message: str) -> bool:
    """Check if message contains activity-related keywords."""
    msg_lower = message.lower()
    return any(kw in msg_lower for kw in ACTIVITY_KEYWORDS)


def _extract_meaningful_words(message: str) -> list[str]:
    """Extract meaningful Korean/English words from message."""
    # Remove common stop words and short tokens
    STOP = {"해줘", "해주세요", "주세요", "이번", "이거", "이", "이것", "그", "그거",
            "저", "저거", "우리", "이", "를", "을", "이", "가", "은", "는",
            "에서", "으로", "에게", "으로", "에", "와", "과", "도", "만", "부터", "까지",
            "합니다", "합시다", "합시요", "해줘", "줘", "해", "좀", "를", "을"}

    # Split by spaces and punctuation
    tokens = re.split(r'[\s,\.!?()]+', message)
    words = [t.strip() for t in tokens if len(t.strip()) >= 2 and t.strip() not in STOP]
    return words[:15]  # max 15 words


def _extract_date(message: str) -> date | None:
    """Try to extract a date from the message."""
    # YYYY-MM-DD format
    m = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})', message)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass

    # Korean date: N월 M일
    m = re.search(r'(\d{1,2})월\s*(\d{1,2})일', message)
    if m:
        try:
            year = date.today().year
            return date(year, int(m.group(1)), int(m.group(2)))
        except ValueError:
            pass

    # "오늘" (today)
    if "오늘" in message:
        return date.today()

    return None


def _build_draft(message: str) -> dict | None:
    """Build an activity draft from the message."""
    # Try to extract a reasonable title
    title = _extract_draft_title(message)
    if not title:
        return None

    extracted_date = _extract_date(message)
    location = _extract_location(message)

    return {
        "title": title,
        "activity_date": str(extracted_date) if extracted_date else None,
        "location": location,
        "description": f"{message[:200]}에서 추출한 활동 초안입니다." if len(message) > 0 else None,
    }


def _extract_draft_title(message: str) -> str | None:
    """Heuristically extract an activity title from message."""
    # Korean activity keyword patterns
    TITLE_PATTERNS = [
        r'([\w\s]{2,20}(?:스터디|세미나|회의|행사|OT|MT|모임|워크숍|발표|교육|공모전))',
        r'((?:신입|정기|월례|특별|임시)\s*[\w\s]{1,15}(?:회|모임|행사|교육))',
        r'(\d{1,2}월\s*[\w\s]{2,20})',
    ]

    for pattern in TITLE_PATTERNS:
        m = re.search(pattern, message)
        if m:
            title = m.group(1).strip()
            if len(title) >= 3:
                return title[:60]

    # Fallback: use first meaningful noun phrase
    words = _extract_meaningful_words(message)
    if words:
        # Take first 3-4 words as title
        candidate = " ".join(words[:3])
        if len(candidate) >= 3:
            return candidate[:60]

    return None


def _extract_location(message: str) -> str | None:
    """Heuristically extract a location from message."""
    LOCATION_PATTERNS = [
        r'([\w]+(?:실|관|홀|센터|강당|도서관|카페|식당|동아리방|사무실))',
        r'([\w]+\s*[0-9]+호)',
        r'(온라인|비대면|ZOOM|Teams|Discord)',
    ]

    for pattern in LOCATION_PATTERNS:
        m = re.search(pattern, message)
        if m:
            return m.group(1).strip()

    return None
