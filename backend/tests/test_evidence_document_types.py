"""Tests for evidence document type expansion (Task 43)."""
from __future__ import annotations

from app.models.receipt import DOCUMENT_TYPE_LABELS


def test_all_expected_document_types_exist() -> None:
    expected = {
        "receipt", "business_registration", "bankbook_copy",
        "transfer_confirmation", "invoice", "quote",
        "transaction_statement", "other", "unknown",
    }
    assert expected == set(DOCUMENT_TYPE_LABELS.keys())


def test_receipt_label() -> None:
    assert DOCUMENT_TYPE_LABELS["receipt"] == "영수증"


def test_business_registration_label() -> None:
    assert DOCUMENT_TYPE_LABELS["business_registration"] == "사업자등록증"


def test_bankbook_copy_label() -> None:
    assert DOCUMENT_TYPE_LABELS["bankbook_copy"] == "통장 사본"


def test_transfer_confirmation_label() -> None:
    assert DOCUMENT_TYPE_LABELS["transfer_confirmation"] == "계좌이체 확인서"


def test_unknown_label() -> None:
    assert DOCUMENT_TYPE_LABELS["unknown"] == "미분류"


def test_other_label() -> None:
    assert DOCUMENT_TYPE_LABELS["other"] == "기타 증빙"
