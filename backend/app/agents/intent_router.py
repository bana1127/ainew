"""Rule-based intent router for the Assistant Command Center.

This module classifies user requests into one of:
  receipt_analysis
  bank_statement_import
  payment_matching             - 거래내역에서 회비/납부 매칭
  bulk_membership_fee_mark_paid - 전체 회비 일괄 완납 처리 (Task 28)
  activity_report_generate
  activity_fee_generate        (Task 17)
  activity_link                (Task 17)
  activity_create              (Task 17)
  unknown

Rules are applied in order of priority. No LLM calls are made here.
"""
from __future__ import annotations

from dataclasses import dataclass
import re

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
BANK_EXTS = {".xls", ".xlsx", ".csv"}

BANK_KEYWORDS = {"거래내역", "입금", "출금", "계좌", "은행"}
# payment_matching: 반드시 거래내역/통장내역을 포함해야 매칭으로 간다
BANK_MATCHING_KEYWORDS = {"거래내역에서", "통장내역", "통장에서", "이 거래내역", "거래내역으로"}
# 회비 키워드 (payment_type=membership_fee)
MEMBERSHIP_FEE_KEYWORDS = {"회비", "학기 회비", "부원 회비"}
PAYMENT_KEYWORDS = {"회비", "납부", "미납"}
RECEIPT_KEYWORDS = {"영수증", "결제", "지출", "증빙"}
REPORT_KEYWORDS = {"활동보고서", "보고서", "활동 사진", "초안"}
ACTIVITY_FEE_KEYWORDS = {
    "활동비", "참가비", "참여자 기준", "비용 걷어", "돈 걷어",
    "납부 대상 만들어", "납부대상", "활동 참가비", "걷어줘",
}
# 회비 일괄 완납 처리 — payment_matching이 아닌 별도 intent (Task 28)
BULK_MEMBERSHIP_FEE_MARK_PAID_KEYWORDS = {
    "전체 회비 완납", "멤버들 전부 회비", "전부 회비",
    "회비 완납 처리", "회비에 맞춰서 완납", "회비 전부 납부",
    "부원들 회비 다 냈", "부원 회비 전부", "회비 일괄 완납",
    "전원 회비 완납", "회원 회비 완납",
    "각각 회비에 맞춰서 완납", "회비에 맞춰 완납",
}
# Keywords that indicate a manual status change (take priority over activity_fee_generate)
PAYMENT_MARK_KEYWORDS = {
    "납부했어", "납부했습니다", "냈어", "냈습니다",
    "입금했어", "입금했습니다", "돈 냈어", "돈 냈습니다",
    "납부 완료로 바꿔", "납부로 바꿔", "납부로 처리",
    "납부 처리해줘", "납부 처리", "납부완료로", "납부완료",
    "미납을 납부", "상태 바꿔줘", "지불했어", "지불했습니다",
    "냈으니", "납부 했으니", "납부했으니",
    # Submission / transfer verbs + standalone completion phrase
    "제출했어", "제출했습니다", "제출 했어", "제출 했습니다",
    "보냈어", "보냈습니다", "송금했어", "송금했습니다",
    "납부 완료",
}
NAME_NOISE_WORDS = {
    "학생", "부원", "회원", "활동비", "회비", "납부", "미납", "완료", "완료로",
    "상태", "처리", "반영", "제출", "입금", "송금", "금액", "만원",
    "바꿔", "바꿔줘", "수정", "수정해", "수정해줘", "맞춰", "맞춰줘",
}
ACTIVITY_LINK_KEYWORDS = {"연결해줘", "연결해", "연결", "증빙으로", "이 활동에"}
ACTIVITY_CREATE_KEYWORDS = {"새 활동", "활동 만들기", "활동 생성", "활동을 만들어"}
ACTIVITY_CREATE_FILE_KEYWORDS = {
    "활동 만들", "활동 생성", "새 활동", "신규 활동", "명단으로", "파일로 활동",
    "참여자 등록", "명단 추가", "신청서 등록", "신청자 등록",
    # Explicit roster-import phrases that must create an activity
    "명단도",       # "명단도 등록해줘"
    "명단 등록",    # "명단 등록해줘"
    "명단도 올려", "명단도 넣어", "명단 올려",
    "참여자 올려", "참여자 넣어", "인원 등록",
}
ROSTER_KEYWORDS = {"명단", "부원", "roster", "명단도", "인원", "참여자"}
APPLICATION_FORM_KEYWORDS = {"신청서", "신청자", "신청", "application", "apply"}
# Filename/keyword hints that signal an application/feedback form rather than a roster
_APPLICATION_FORM_FILENAME_HINTS = ("신청", "모집", "응답", "application", "apply")
# Activity fee transaction matching (activity_id must be linked)
ACTIVITY_FEE_TRANSACTION_MATCH_KEYWORDS = {
    "활동비 매칭해줘", "거래내역으로 활동비", "활동비 입금 확인",
    "참가자 활동비 입금", "활동비 거래내역 매칭", "이 거래내역으로 활동비 매칭",
    "현재 활동 활동비 매칭", "활동비 납부 확인해줘",
    "활동비 입금 확인해줘", "참가자들 활동비 입금", "참가자 활동비 확인",
    "활동비 거래 확인", "이 활동 활동비 매칭",
}
# Membership fee record generation (create payment records for the semester)
MEMBERSHIP_FEE_GENERATE_KEYWORDS = {
    "회비 대상 생성", "회비 납부 대상 생성", "이번 학기 회비 생성",
    "이번 학기 회비 대상", "학기 회비 대상", "회비 대상자 생성",
    "회비 납부 대상자", "회비 생성해줘", "회비 대상 만들어",
}
# Participant import into an existing activity (activity_id already linked)
PARTICIPANT_IMPORT_KEYWORDS = {
    "참여자로 등록", "참가자로 등록", "참여자 등록해줘", "참가자 등록해줘",
    "참여자로 넣어줘", "참가자로 넣어줘", "명단 등록해줘", "이 명단 등록해줘",
    "이 신청서 참여자로", "참가자 추가해줘", "참여자 추가해줘",
    "참여자로 반영", "참가자로 반영",
}


@dataclass
class IntentResult:
    intent: str
    confidence: float
    reason: str


def _has_keyword(message: str, keywords: set[str]) -> bool:
    return any(kw in message for kw in keywords)


def _has_member_name_candidate(message: str) -> bool:
    suffixes = ("학생", "부원", "회원", "님", "씨", "이가", "이는", "이를", "가", "이", "은", "는", "의", "을", "를")
    suffix_pat = "|".join(suffixes)
    patterns = (
        rf'([가-힣]{{2,4}})(?:{suffix_pat})',
        r'(^|[\s,])([가-힣]{2,4})(?=\s|$)',
    )
    for pattern in patterns:
        for match in re.finditer(pattern, message):
            candidate = match.group(1) if match.lastindex == 1 else match.group(2)
            if candidate and candidate not in NAME_NOISE_WORDS:
                return True
    return False


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
    has_file = bool(file_names)

    if has_file and _has_keyword(msg, ACTIVITY_CREATE_FILE_KEYWORDS):
        joined_names = " ".join(file_names).lower()
        # Check filename for application-form hints first (more specific)
        if any(kw in joined_names for kw in _APPLICATION_FORM_FILENAME_HINTS) or \
                _has_keyword(msg, APPLICATION_FORM_KEYWORDS):
            return IntentResult("activity_create_with_application_form", 0.92,
                                "Activity creation with application form keywords")
        if _has_keyword(msg, ROSTER_KEYWORDS):
            return IntentResult("activity_create_with_roster", 0.92,
                                "Activity creation with roster keywords")
        return IntentResult("activity_create_with_file", 0.86, "Activity creation with uploaded file")

    # 0. Participant import into an already-linked activity. This is narrower
    # than the activity-create file flow above so "명단 등록해줘" keeps creating
    # a new activity unless the orchestrator has an activity_id context.
    # 0b. Activity fee transaction matching
    if _has_keyword(msg, ACTIVITY_FEE_TRANSACTION_MATCH_KEYWORDS):
        return IntentResult("activity_fee_transaction_match", 0.93, "Activity fee transaction match keywords")

    if has_bank and _has_keyword(msg, PARTICIPANT_IMPORT_KEYWORDS):
        return IntentResult("participant_import", 0.93, "Spreadsheet + participant import keywords")

    # 1b. Spreadsheet + roster/명단 keywords — treat as roster import regardless of other keywords.
    #     This catches "활동비 2만원, 명단도 등록해줘" which has "활동비" but also "명단"+"xlsx".
    #     Must come BEFORE activity_fee_generate so "활동비" doesn't steal priority.
    if has_bank and _has_keyword(msg, ROSTER_KEYWORDS):
        # Distinguish roster vs application form by filename
        joined_names = " ".join(file_names).lower()
        if any(kw in joined_names for kw in _APPLICATION_FORM_FILENAME_HINTS):
            return IntentResult("activity_create_with_application_form", 0.90,
                                "Spreadsheet + application form keywords in filename")
        return IntentResult("activity_create_with_roster", 0.90,
                            "Spreadsheet + roster/명단 keywords in message")

    # 2a-00. Membership fee record generation (before bulk mark paid to avoid overlap)
    if _has_keyword(msg, MEMBERSHIP_FEE_GENERATE_KEYWORDS):
        return IntentResult("membership_fee_generate", 0.88, "Membership fee generate keywords")

    # 2a-0. Bulk membership fee mark paid (HIGHEST priority over payment_matching)
    # e.g. "전체 회비 완납 처리해줘", "현재 멤버 전부 각각 회비에 맞춰서 완납 처리해줘"
    if _has_keyword(msg, BULK_MEMBERSHIP_FEE_MARK_PAID_KEYWORDS):
        return IntentResult("bulk_membership_fee_mark_paid", 0.95, "Bulk membership fee mark paid keywords")

    # 2a. Manual payment status update (must come BEFORE activity_fee_generate)
    # Handles: "박민서 학생이 활동비 15000원을 납부했어"
    if _has_keyword(msg, PAYMENT_MARK_KEYWORDS) and _has_member_name_candidate(msg):
        return IntentResult("payment_manual_update", 0.92, "Manual payment status change keywords")

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

    # 5. Payment matching: only when bank/transaction keywords are explicitly present
    # "거래내역에서 회비 확인해줘", "통장내역 회비랑 매칭해줘"
    if _has_keyword(msg, BANK_MATCHING_KEYWORDS) and _has_keyword(msg, PAYMENT_KEYWORDS):
        return IntentResult("payment_matching", 0.88, "Bank matching + payment keywords")
    # Legacy fallback: plain payment keywords without bulk intent
    if _has_keyword(msg, PAYMENT_KEYWORDS) and not _has_keyword(msg, MEMBERSHIP_FEE_KEYWORDS):
        return IntentResult("payment_matching", 0.75, "Payment keywords in message")

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
