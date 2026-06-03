from datetime import datetime
from uuid import UUID

from app.schemas.common import ORMModel


class PaymentRecordBase(ORMModel):
    member_id: UUID
    period: str
    payment_type: str = "membership_fee"
    required_amount: int = 0
    paid_amount: int = 0
    status: str = "unpaid"
    transaction_id: UUID | None = None


class PaymentRecordCreate(PaymentRecordBase):
    pass


class PaymentRecordUpdate(ORMModel):
    period: str | None = None
    payment_type: str | None = None
    required_amount: int | None = None
    paid_amount: int | None = None
    status: str | None = None
    transaction_id: UUID | None = None
    fee_tier: str | None = None
    fee_rule_reason: str | None = None
    joined_term: str | None = None
    current_term: str | None = None


class PaymentRecordRead(PaymentRecordBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    # Member info (populated by enrichment)
    member_name: str | None = None
    student_id: str | None = None
    department: str | None = None
    # Activity context for activity_fee records
    activity_report_id: UUID | None = None
    activity_title: str | None = None
    # Refund tracking (Task 21)
    refund_status: str | None = None
    refund_amount: int | None = None
    fee_tier: str | None = None
    fee_rule_reason: str | None = None
    joined_term: str | None = None
    current_term: str | None = None
