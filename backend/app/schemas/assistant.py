from __future__ import annotations

from uuid import UUID
from pydantic import BaseModel


class AssistantExecuteRequest(BaseModel):
    message: str | None = None
    file_ids: list[UUID] = []
    requested_intent: str = "auto"
    auto_apply: bool = False
    period: str | None = None
    payment_type: str | None = "membership_fee"
    required_amount: int | None = None
    # Task 17: Activity-aware assistant
    activity_id: UUID | None = None
    activity_mode: str = "auto"  # auto | link_existing | create_new | none
    create_activity_if_missing: bool = False


class AssistantExecuteResponse(BaseModel):
    intent: str
    confidence: float
    agent_flow: list[str]
    result_type: str
    result: dict
    requires_confirmation: bool
    message: str
    # Task 11: apply_payload and detail_url for Human-in-the-loop UX
    apply_payload: dict | None = None
    detail_url: str | None = None
    # Task 17: Activity context
    activity_context: dict | None = None
    activity_candidates: list[dict] | None = None
    activity_draft: dict | None = None
