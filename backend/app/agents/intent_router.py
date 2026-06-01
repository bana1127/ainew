"""Rule-based intent router for the Assistant Command Center.

This module classifies user requests into one of:
  receipt_analysis
  bank_statement_import
  payment_matching
  activity_report_generate
  activity_fee_generate   (Task 17)
  activity_link           (Task 17)
  activity_create         (Task 17)
  unknown

Rules are applied in order of priority. No LLM calls are made here.
"""
from __future__ import annotations

from dataclasses import dataclass

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
BANK_EXTS = {".xls", ".xlsx", ".csv"}

BANK_KEYWORDS = {"거래내역", "입금", "출금", "계좌", "은행"}
PAYMENT_KEYWORDS = {"회비", "납부", "미납"}
RECEIPT_KEYWORDS = {"영수증", "결제", "지출", "증빙"}
REPORT_KEYWORDS = {"활동보고서", "보고서", "활동 사진", "초안"}
ACTIVITY_FEE_KEYWORDS = {
    "활동비", "참가비", "참여자 기준", "비용 걷어", "돈 걷어",
    "납부 대상 만들어", "납부대상", "활동 참가비", "걷어줘",
}
ACTIVITY_LINK_KEYWORDS = {"연결해줘", "연결해", "연결", "증빙으로", "이 활동에"}
ACTIVITY_CREATE_KEYWORDS = {"새 활동", "활동 만들기", "활동 생성", "활동을 만들어"}


@dataclass
class IntentResult:
    intent: str
    confidence: float
    reason: str


def _has_keyword(message: str, keywords: set[str]) -> bool:
    return any(kw in message for kw in keywords)


def _file_exts(file_names: list[str]) -> set[str]:
    exts: set[str] = set()
    for name in file_names:
        dot = name.rfind(".")
        if dot != -1:
            exts.add(name[dot:].lower())
    return exts


def route(
    message: str | None,
    file_names: list[str],
    requested_intent: str = "auto",
) -> IntentResult:
    """Determine intent from message and file list."""

    # 1. If user explicitly chose a non-auto intent, trust it
    if requested_intent and requested_intent != "auto":
        return IntentResult(
            intent=requested_intent,
            confidence=1.0,
            reason="User explicitly selected intent",
        )

    msg = (message or "").strip()
    exts = _file_exts(file_names)
    has_image = bool(exts & IMAGE_EXTS)
    has_bank = bool(exts & BANK_EXTS)

    # 2. Activity fee generation (check before general payment)
    if _has_keyword(msg, ACTIVITY_FEE_KEYWORDS):
        return IntentResult("activity_fee_generate", 0.88, "Activity fee keywords in message")

    # 3. Activity creation
    if _has_keyword(msg, ACTIVITY_CREATE_KEYWORDS):
        return IntentResult("activity_create", 0.85, "Activity creation keywords in message")

    # 4. Bank statement import: spreadsheet file present
    if has_bank:
        if _has_keyword(msg, BANK_KEYWORDS) or _has_keyword(msg, PAYMENT_KEYWORDS):
            return IntentResult("bank_statement_import", 0.85, "Spreadsheet file + bank/payment keywords")
        return IntentResult("bank_statement_import", 0.75, "Spreadsheet file detected")

    # 5. Payment matching: keywords without file (use existing transactions)
    if _has_keyword(msg, PAYMENT_KEYWORDS):
        return IntentResult("payment_matching", 0.80, "Payment keywords in message")

    # 6. Bank statement from message keywords only
    if _has_keyword(msg, BANK_KEYWORDS):
        return IntentResult("bank_statement_import", 0.70, "Bank keywords in message")

    # 7. Activity linking (receipt + link keywords)
    if _has_keyword(msg, ACTIVITY_LINK_KEYWORDS):
        return IntentResult("activity_link", 0.75, "Activity link keywords")

    # 8. Receipt analysis: image file + receipt keywords
    if has_image and _has_keyword(msg, RECEIPT_KEYWORDS):
        return IntentResult("receipt_analysis", 0.85, "Image file + receipt keywords")

    # 9. Activity report: report keywords
    if _has_keyword(msg, REPORT_KEYWORDS):
        return IntentResult("activity_report_generate", 0.75, "Report keywords in message")

    # 10. Image file only with no clear message
    if has_image:
        return IntentResult("receipt_analysis", 0.45, "Image file with ambiguous message")

    # 11. Fallback
    return IntentResult(
        "unknown",
        0.0,
        "요청을 정확히 분류하지 못했습니다. 영수증 분석, 거래내역서 분석, 납부 매칭, 활동 보고서 생성 중 하나를 선택해 다시 실행해 주세요.",
    )
