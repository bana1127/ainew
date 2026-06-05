"""Tests for evidence document type detection (Task 43 Hotfix)."""
from __future__ import annotations

from app.services.evidence_parser_service import (
    detect_document_type_from_text,
    is_amount_required,
    policy_for_document_type,
)


def test_detect_business_registration_from_keyword() -> None:
    text = "사업자등록증\n대표자: 홍길동\n사업자등록번호: 123-45-67890"
    assert detect_document_type_from_text(text) == "business_registration"


def test_detect_bankbook_copy_from_keyword() -> None:
    text = "예금주: 홍길동\n계좌번호: 123-456-789012\n은행: 국민은행"
    assert detect_document_type_from_text(text) == "bankbook_copy"


def test_detect_transfer_confirmation_from_keyword() -> None:
    text = "이체확인증\n보내는분: 홍길동\n받는분: 김철수\n이체금액: 50,000원"
    assert detect_document_type_from_text(text) == "transfer_confirmation"


def test_detect_receipt_from_keyword() -> None:
    text = "영수증\n승인번호: 123456\n결제금액: 15,000원\n가맹점: 편의점"
    assert detect_document_type_from_text(text) == "receipt"


def test_detect_unknown_for_empty_text() -> None:
    assert detect_document_type_from_text(None) == "unknown"
    assert detect_document_type_from_text("") == "unknown"


def test_detect_unknown_for_unrecognized_text() -> None:
    text = "그냥 임의 텍스트입니다"
    assert detect_document_type_from_text(text) == "unknown"


def test_business_registration_priority_over_receipt() -> None:
    """사업자등록증 키워드가 있으면 영수증보다 우선."""
    text = "사업자등록증\n합계금액: 100,000원"
    assert detect_document_type_from_text(text) == "business_registration"


def test_is_amount_required_for_receipt() -> None:
    assert is_amount_required("receipt") is True


def test_is_amount_required_for_business_registration() -> None:
    assert is_amount_required("business_registration") is False


def test_is_amount_required_for_bankbook_copy() -> None:
    assert is_amount_required("bankbook_copy") is False


def test_policy_for_business_registration_no_amount() -> None:
    status, need_check, reason = policy_for_document_type("business_registration", 0)
    assert status == "valid"
    assert need_check is False


def test_policy_for_bankbook_copy_no_amount() -> None:
    status, need_check, reason = policy_for_document_type("bankbook_copy", None)
    assert status == "valid"
    assert need_check is False


def test_policy_for_receipt_with_no_amount() -> None:
    status, need_check, reason = policy_for_document_type("receipt", 0)
    assert need_check is True


def test_policy_for_receipt_with_amount() -> None:
    status, need_check, reason = policy_for_document_type("receipt", 15000)
    assert need_check is False
