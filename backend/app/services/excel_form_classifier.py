"""Rule-based Excel form type classifier.

Classifies uploaded Excel/CSV files into one of:
  activity_application_form  — 활동 전 신청서
  activity_feedback_form     — 활동 후 활동지/피드백
  bank_statement             — 거래내역서
  member_roster              — 부원 명부
  unknown_excel              — 알 수 없음
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Column keyword sets per form type
# ---------------------------------------------------------------------------

_APPLICATION_KEYWORDS = [
    "신청 시간", "신청시간", "타임스탬프", "이름", "학번", "전화번호", "연락처",
    "참여 가능 시간", "참여가능시간", "타임", "선택 옵션", "선택옵션", "향조 선택",
    "향조선택", "신청 사유", "신청사유", "지원 동기", "지원동기", "참여 인원",
    "희망 시간", "희망시간",
]

_FEEDBACK_KEYWORDS = [
    "가져온 향수", "인상 깊었던 향", "인상깊었던향", "첫 느낌", "첫느낌",
    "떠오르는 이미지", "떠오르는이미지", "개선점", "후기", "피드백", "만족도",
    "활동 후기", "활동후기", "소감", "건의사항", "좋았던 점", "좋았던점",
    "아쉬웠던 점", "아쉬웠던점", "참여 소감", "참여소감",
]

_BANK_KEYWORDS = [
    "거래일시", "거래 일시", "입금", "출금", "잔액", "적요", "입금자", "거래내용",
    "거래금액", "거래 금액", "통장 잔액", "통장잔액", "구분", "거래구분",
]

_MEMBER_ROSTER_KEYWORDS = [
    "학과", "이메일", "기수", "상태", "가입일", "입회일", "연락처",
]

# Weights — higher = stronger signal
_APPLICATION_WEIGHTS = {
    "신청 시간": 3, "신청시간": 3, "타임스탬프": 2,
    "학번": 2, "전화번호": 2, "연락처": 2,
    "타임": 2, "선택 옵션": 2, "선택옵션": 2,
    "향조 선택": 3, "향조선택": 3,
    "이름": 1,
}
_FEEDBACK_WEIGHTS = {
    "가져온 향수": 3, "인상 깊었던 향": 3, "첫 느낌": 2, "떠오르는 이미지": 2,
    "개선점": 2, "후기": 2, "피드백": 2, "만족도": 2, "활동 후기": 3,
    "소감": 1,
}
_BANK_WEIGHTS = {
    "거래일시": 3, "거래 일시": 3, "입금": 2, "출금": 2,
    "잔액": 2, "적요": 3, "입금자": 2, "거래내용": 2,
}
_MEMBER_WEIGHTS = {
    "학과": 2, "이메일": 2, "기수": 3, "상태": 1, "가입일": 3, "입회일": 3,
}

FORM_TYPES = [
    "activity_application_form",
    "activity_feedback_form",
    "bank_statement",
    "member_roster",
    "unknown_excel",
]


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class FormClassificationResult:
    form_type: str
    confidence: float
    matched_columns: list[str] = field(default_factory=list)
    reason: str = ""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalize(text: str) -> str:
    """Strip whitespace and collapse internal spaces."""
    return re.sub(r"\s+", " ", text.strip())


def _score_headers(
    headers: list[str],
    keywords: list[str],
    weights: dict[str, int],
) -> tuple[float, list[str]]:
    """Return (raw_score, matched_columns)."""
    norm_headers = [_normalize(h) for h in headers]
    matched: list[str] = []
    score = 0.0
    for kw in keywords:
        norm_kw = _normalize(kw)
        for nh, orig in zip(norm_headers, headers):
            if norm_kw in nh or nh in norm_kw:
                if orig not in matched:
                    matched.append(orig)
                    score += weights.get(kw, 1)
                break
    return score, matched


def _filename_hint(filename: str | None) -> str | None:
    """Derive a likely form type hint from the file name."""
    if not filename:
        return None
    fn_lower = filename.lower()
    if any(k in fn_lower for k in ["신청", "모집", "application", "apply"]):
        return "activity_application_form"
    if any(k in fn_lower for k in ["활동지", "피드백", "feedback", "후기", "소감"]):
        return "activity_feedback_form"
    if any(k in fn_lower for k in ["거래", "통장", "statement", "은행"]):
        return "bank_statement"
    if any(k in fn_lower for k in ["명부", "roster", "부원", "회원"]):
        return "member_roster"
    return None


# ---------------------------------------------------------------------------
# Main classifier
# ---------------------------------------------------------------------------

def classify_excel_form(
    headers: list[str],
    filename: str | None = None,
) -> FormClassificationResult:
    """Classify an Excel file based on column headers and optional filename.

    Returns FormClassificationResult with form_type, confidence (0-1),
    matched_columns, and a human-readable reason string.
    """
    if not headers:
        return FormClassificationResult(
            form_type="unknown_excel",
            confidence=0.0,
            reason="헤더 없음",
        )

    app_score, app_cols = _score_headers(headers, _APPLICATION_KEYWORDS, _APPLICATION_WEIGHTS)
    fb_score, fb_cols = _score_headers(headers, _FEEDBACK_KEYWORDS, _FEEDBACK_WEIGHTS)
    bank_score, bank_cols = _score_headers(headers, _BANK_KEYWORDS, _BANK_WEIGHTS)
    roster_score, roster_cols = _score_headers(headers, _MEMBER_ROSTER_KEYWORDS, _MEMBER_WEIGHTS)

    # Check for generic name + student_id — adds to application & roster
    norm_headers = [_normalize(h) for h in headers]
    has_name = any("이름" in h for h in norm_headers)
    has_student_id = any("학번" in h for h in norm_headers)
    if has_name and has_student_id:
        app_score += 2
        roster_score += 1

    scores = {
        "activity_application_form": app_score,
        "activity_feedback_form": fb_score,
        "bank_statement": bank_score,
        "member_roster": roster_score,
    }
    matched_map = {
        "activity_application_form": app_cols,
        "activity_feedback_form": fb_cols,
        "bank_statement": bank_cols,
        "member_roster": roster_cols,
    }

    best_type = max(scores, key=lambda k: scores[k])
    best_score = scores[best_type]

    if best_score == 0:
        # Filename hint fallback
        hint = _filename_hint(filename)
        if hint:
            return FormClassificationResult(
                form_type=hint,
                confidence=0.3,
                reason="파일명 기반 판별 (컬럼 매칭 없음)",
            )
        return FormClassificationResult(
            form_type="unknown_excel",
            confidence=0.0,
            reason="알 수 없는 형식",
        )

    # Normalize confidence: cap at 1.0
    max_possible = {
        "activity_application_form": 18,
        "activity_feedback_form": 18,
        "bank_statement": 14,
        "member_roster": 11,
    }
    raw_max = max_possible.get(best_type, 10)
    confidence = min(best_score / raw_max, 1.0)

    # Filename hint bonus
    hint = _filename_hint(filename)
    if hint == best_type:
        confidence = min(confidence + 0.1, 1.0)
    elif hint and hint != best_type and confidence < 0.6:
        # Weak match + conflicting hint → unknown
        return FormClassificationResult(
            form_type="unknown_excel",
            confidence=0.3,
            matched_columns=matched_map[best_type],
            reason=f"파일명({hint})과 컬럼({best_type}) 불일치, 사용자 확인 필요",
        )

    reason_map = {
        "activity_application_form": "신청자 정보와 선택 옵션 컬럼이 확인되었습니다.",
        "activity_feedback_form": "활동 후기 및 피드백 컬럼이 확인되었습니다.",
        "bank_statement": "거래내역서 형식(거래일시, 입금, 출금, 잔액)이 확인되었습니다.",
        "member_roster": "부원 명부 형식(학과, 기수 등)이 확인되었습니다.",
    }

    return FormClassificationResult(
        form_type=best_type,
        confidence=round(confidence, 3),
        matched_columns=matched_map[best_type],
        reason=reason_map.get(best_type, ""),
    )
