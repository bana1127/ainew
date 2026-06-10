"""Evidence document type detection from OCR text (Task 43 Hotfix)."""
from __future__ import annotations

# Document type detection keywords (Korean OCR text)
_BUSINESS_REGISTRATION_KEYWORDS = [
    "사업자등록증", "사업자등록번호", "대표자", "개업연월일", "사업장소재지",
    "사업장 소재지", "업태", "종목", "세무서", "국세청", "부가가치세법",
    "법인명", "상호", "법인등록번호",
]

_BANKBOOK_COPY_KEYWORDS = [
    "통장", "계좌번호", "예금주", "은행", "입출금", "보통예금",
    "금융기관", "은행장", "지점장",
]

_TRANSFER_CONFIRMATION_KEYWORDS = [
    "이체확인", "이체확인증", "송금확인", "입금계좌", "출금계좌",
    "받는분", "보내는분", "이체금액", "거래일시", "수취인", "송금",
    "이체완료", "계좌이체",
]

_RECEIPT_KEYWORDS = [
    "영수증", "승인번호", "카드번호", "결제금액", "합계금액",
    "공급가액", "부가세", "가맹점", "매출전표", "현금영수증",
    "카드승인", "단말기",
]

_INVOICE_KEYWORDS = [
    "청구서", "청구금액", "납부기한", "납부금액",
]

_QUOTE_KEYWORDS = [
    "견적서", "견적금액", "유효기간",
]

_STATEMENT_KEYWORDS = [
    "거래명세서", "거래명세표", "품명", "수량", "단가",
]

_ACTIVITY_PHOTO_KEYWORDS = [
    "activity photo", "activity_image", "group photo", "people visible",
    "person visible", "participant", "participants", "people", "person",
    "face", "faces", "활동사진", "활동 사진", "단체사진", "단체 사진",
    "사람", "인물", "얼굴", "참가자", "참여자", "회원", "동아리 활동",
]


def detect_document_type_from_text(raw_text: str | None) -> str:
    """Detect document_type from OCR raw text. Returns 'unknown' if no match."""
    if not raw_text:
        return "unknown"

    text_lower = raw_text.lower()

    def _has_keyword(keywords: list[str]) -> bool:
        return any(kw.lower() in text_lower for kw in keywords)

    # Priority order matters: most specific first
    if _has_keyword(_BUSINESS_REGISTRATION_KEYWORDS):
        return "business_registration"
    if _has_keyword(_TRANSFER_CONFIRMATION_KEYWORDS):
        return "transfer_confirmation"
    if _has_keyword(_BANKBOOK_COPY_KEYWORDS):
        return "bankbook_copy"
    if _has_keyword(_RECEIPT_KEYWORDS):
        return "receipt"
    if _has_keyword(_INVOICE_KEYWORDS):
        return "invoice"
    if _has_keyword(_QUOTE_KEYWORDS):
        return "quote"
    if _has_keyword(_STATEMENT_KEYWORDS):
        return "transaction_statement"
    return "unknown"


def looks_like_activity_photo(
    raw_text: str | None,
    file_name: str | None = None,
    mime_type: str | None = None,
    amount: int | None = None,
    extracted_document_type: str | None = None,
) -> bool:
    """Return True when image analysis indicates a people/activity photo.

    Activity photos usually have no amount/OCR text. We only auto-classify them
    when the file is an image and the analysis or filename contains people/activity
    cues, so ordinary receipt images are not silently reclassified.
    """
    if extracted_document_type == "activity_photo":
        return True

    if mime_type and not mime_type.startswith("image/"):
        return False

    amount_val = int(amount or 0)
    if amount_val > 0:
        return False

    text = " ".join(part for part in [raw_text, file_name] if part).lower()
    if not text:
        return False

    return any(keyword.lower() in text for keyword in _ACTIVITY_PHOTO_KEYWORDS)


def is_amount_required(document_type: str) -> bool:
    """Return True if amount is required for this document type to be valid."""
    return document_type in {"receipt", "transfer_confirmation", "invoice", "quote", "transaction_statement"}


def policy_for_document_type(document_type: str, amount: int | None) -> tuple[str, bool, str]:
    """Return (evidence_status, need_check, reason) based on document type and amount.

    Non-amount documents (business_registration, bankbook_copy) don't need an amount.
    """
    amount_val = int(amount or 0)

    if document_type == "business_registration":
        return "valid", False, "사업자등록증은 금액 없어도 유효한 증빙입니다."

    if document_type == "bankbook_copy":
        return "valid", False, "통장 사본은 금액 없어도 유효한 증빙입니다."

    if document_type == "activity_photo":
        return "valid", False, "활동 사진은 금액 없는 증빙으로 정상 처리됩니다."

    if document_type in {"receipt", "transfer_confirmation", "invoice"}:
        if amount_val <= 0:
            return "need_check", True, "금액 정보가 없습니다. 직접 확인 후 입력하세요."
        return "pending", False, "금액 정보가 있습니다."

    # other, unknown, quote, transaction_statement → pending
    return "pending", False, "증빙이 저장되었습니다."
