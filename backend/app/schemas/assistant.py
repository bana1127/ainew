from __future__ import annotations

from uuid import UUID
from typing import Any

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


class AssistantChatContext(BaseModel):
    page: str | None = None
    activity_id: UUID | None = None
    last_activity_id: UUID | None = None
    period: str | None = None
    current_page: str | None = None
    current_activity_id: UUID | None = None
    current_tab: str | None = None
    visible_filters: dict[str, Any] | None = None
    quarter: str | None = None


class AssistantChatRequest(BaseModel):
    message: str
    context: AssistantChatContext | dict[str, Any] | None = None


class AssistantChatLink(BaseModel):
    label: str
    url: str


class AssistantChatResponse(BaseModel):
    answer: str
    intent: str
    data_sources: list[str]
    links: list[AssistantChatLink]
    confidence: float
    summary: list[dict[str, str]] = []
    items: list[dict[str, Any]] = []
    zero_reasons: list[str] = []
    scope: str | None = None
    context_used: dict[str, Any] = {}
