from __future__ import annotations

from app.models import Receipt
from app.schemas.receipt import ReceiptCreate, VALID_DOCUMENT_TYPES
from app.services.evidence_parser_service import (
    looks_like_activity_photo,
    policy_for_document_type,
)


def test_activity_photo_document_type_is_supported():
    assert "activity_photo" in VALID_DOCUMENT_TYPES


def test_activity_photo_receipt_allows_null_amount():
    payload = ReceiptCreate(
        document_type="activity_photo",
        activity_report_id=None,
        amount=None,
        evidence_status="valid",
        need_check=False,
    )
    receipt = Receipt(**payload.model_dump())

    assert receipt.document_type == "activity_photo"
    assert receipt.amount is None
    assert receipt.evidence_status == "valid"


def test_activity_photo_policy_is_valid_without_amount():
    status, need_check, reason = policy_for_document_type("activity_photo", None)

    assert status == "valid"
    assert need_check is False
    assert "활동 사진" in reason


def test_people_image_analysis_can_be_activity_photo():
    assert looks_like_activity_photo(
        raw_text="activity photo: people visible during club event",
        file_name="club_event.jpg",
        mime_type="image/jpeg",
        amount=0,
    )


def test_receipt_image_with_amount_is_not_activity_photo():
    assert not looks_like_activity_photo(
        raw_text="activity photo printed on receipt memo",
        file_name="receipt.jpg",
        mime_type="image/jpeg",
        amount=15000,
    )
