from __future__ import annotations

from pydantic import BaseModel


class MembershipFeePreviewPayload(BaseModel):
    period: str | None = None
    new_member_fee: int = 15000
    existing_member_fee: int = 10000
    executive_fee: int = 0


class MembershipFeePreviewRow(BaseModel):
    member_id: str
    member_name: str
    student_id: str | None = None
    department: str | None = None
    joined_term: str | None = None
    term_code: str | None = None
    current_term: str
    is_officer: bool
    officer_role: str | None = None
    role_label: str
    fee_tier: str
    required_amount: int
    paid_amount: int
    status: str
    fee_rule_reason: str
    existing_record_id: str | None = None
    action: str


class MembershipFeePreviewSummary(BaseModel):
    total_members: int
    current_term: str
    new_member_count: int
    existing_member_count: int
    executive_count: int
    total_required_amount: int
    total_paid_amount: int
    created_count: int
    updated_count: int
    preserved_paid_count: int


class MembershipFeePreviewResponse(BaseModel):
    period: str
    payment_type: str
    current_term: str
    new_member_fee: int
    existing_member_fee: int
    executive_fee: int
    requires_confirmation: bool
    auto_apply: bool
    action_id: str | None
    summary: MembershipFeePreviewSummary
    rows: list[MembershipFeePreviewRow]
