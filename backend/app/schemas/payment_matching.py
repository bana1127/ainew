from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.common import ORMModel


class PaymentMatchingPayload(BaseModel):
    period: str
    payment_type: str = "membership_fee"
    required_amount: int | None = None
    start_date: date | None = None
    end_date: date | None = None
    match_mode: str = "auto"  # auto | membership_fee | activity_fee | selected_activity_fee | none
    activity_id: UUID | None = None  # for selected_activity_fee mode


class PaymentConfirmPayload(BaseModel):
    member_id: UUID
    period: str
    payment_type: str = "membership_fee"
    required_amount: int = 30000
    status: str = "paid"


class PaymentExcludePayload(BaseModel):
    payment_type: str = "other"  # refund, interest, other
    reason: str | None = None


class TransactionMatchItemSchema(ORMModel):
    transaction_id: UUID
    transaction_datetime: datetime | None = None
    memo: str | None = None
    deposit_amount: int
    matched_member_id: UUID | None = None
    matched_member_name: str | None = None
    payment_type: str | None = None
    match_status: str
    score: float | None = None
    reason: str | None = None
    activity_id: UUID | None = None
    activity_title: str | None = None
    match_mode: str | None = None
    expected_amount: int | None = None
    amount_difference: int | None = None
    amount_status: str | None = None
    auto_match: bool = False
    fee_tier: str | None = None


class MemberSummarySchema(ORMModel):
    member_id: UUID
    name: str
    student_id: str | None = None
    department: str | None = None
    required_amount: int
    paid_amount: int
    status: str


class UnpaidPaymentItem(ORMModel):
    member_id: UUID
    name: str
    student_id: str | None = None
    department: str | None = None
    required_amount: int
    paid_amount: int
    status: str
    payment_record_id: UUID | None = None


class PaymentMatchingPreviewSchema(ORMModel):
    period: str
    payment_type: str
    required_amount: int
    total_active_members: int
    total_deposit_transactions: int
    matched_count: int
    need_check_count: int
    excluded_count: int
    unpaid_count: int
    matched_items: list[TransactionMatchItemSchema]
    need_check_items: list[TransactionMatchItemSchema]
    excluded_items: list[TransactionMatchItemSchema]
    unpaid_members: list[MemberSummarySchema]


class PaymentMatchingResultSchema(PaymentMatchingPreviewSchema):
    created_payment_records: int = 0
    updated_payment_records: int = 0
    updated_transactions: int = 0


class PaymentSummaryResponse(ORMModel):
    period: str
    payment_type: str
    required_amount: int
    total_members: int
    paid_count: int
    partial_count: int
    unpaid_count: int
    need_check_count: int
    exempt_count: int = 0
    overpaid_count: int = 0
    missing_record_count: int = 0
    receivable_amount: int = 0
    total_required_amount: int
    total_paid_amount: int
