from datetime import datetime, time
from typing import Any
from uuid import UUID

from app.schemas.common import ORMModel


class NotificationBase(ORMModel):
    type: str
    title: str
    message: str
    severity: str = "info"
    is_read: bool = False
    related_entity_type: str | None = None
    related_entity_id: UUID | None = None


class NotificationCreate(NotificationBase):
    pass


class NotificationUpdate(ORMModel):
    type: str | None = None
    title: str | None = None
    message: str | None = None
    severity: str | None = None
    is_read: bool | None = None
    related_entity_type: str | None = None
    related_entity_id: UUID | None = None


class NotificationRead(NotificationBase):
    id: UUID
    created_at: datetime


REMINDER_TYPES = {
    "membership_fee_due",
    "activity_fee_due",
    "activity_evidence_missing",
    "activity_photo_missing",
    "activity_report_missing",
    "activity_upcoming",
    "evidence_missing",
    "report_missing",
    "calendar_deadline",
    "quarter_settlement",
    "custom",
}


class NotificationRuleBase(ORMModel):
    name: str
    enabled: bool = True
    reminder_type: str
    target_scope: str = "global"
    channel: str = "gmail"
    send_time: time | None = None
    days_before: int | None = None
    days_after: int | None = None
    repeat_interval_days: int | None = None
    max_send_count: int | None = None
    require_confirm_before_send: bool = True
    term: str | None = None
    quarter: str | None = None
    activity_id: UUID | None = None
    conditions: dict[str, Any] | None = None
    template_subject: str
    template_body: str


class NotificationRuleCreate(NotificationRuleBase):
    pass


class NotificationRuleUpdate(ORMModel):
    name: str | None = None
    enabled: bool | None = None
    reminder_type: str | None = None
    target_scope: str | None = None
    channel: str | None = None
    send_time: time | None = None
    days_before: int | None = None
    days_after: int | None = None
    repeat_interval_days: int | None = None
    max_send_count: int | None = None
    require_confirm_before_send: bool | None = None
    term: str | None = None
    quarter: str | None = None
    activity_id: UUID | None = None
    conditions: dict[str, Any] | None = None
    template_subject: str | None = None
    template_body: str | None = None
    deleted_at: datetime | None = None


class NotificationRuleRead(NotificationRuleBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None


class NotificationPreviewItem(ORMModel):
    rule_id: UUID | None = None
    reminder_type: str | None = None
    target_type: str
    target_id: str
    recipient_email: str
    recipient_name: str | None = None
    subject: str
    body: str
    target_url: str | None = None
    reason: str


class NotificationPreviewResponse(ORMModel):
    rule_id: UUID
    count: int
    items: list[NotificationPreviewItem]


class NotificationDeliveryLogBase(ORMModel):
    rule_id: UUID | None = None
    reminder_type: str
    target_type: str
    target_id: str
    recipient_email: str
    recipient_name: str | None = None
    subject: str
    body: str
    target_url: str | None = None
    provider: str = "n8n"
    provider_message_id: str | None = None
    status: str = "pending"
    error_message: str | None = None
    sent_at: datetime | None = None


class NotificationDeliveryLogCreate(NotificationDeliveryLogBase):
    pass


class NotificationDeliveryLogRead(NotificationDeliveryLogBase):
    id: UUID
    created_at: datetime


class NotificationSendResult(ORMModel):
    requested: int
    sent: int
    failed: int
    skipped: int
    logs: list[NotificationDeliveryLogRead]


class NotificationDueResponse(ORMModel):
    count: int
    items: list[NotificationPreviewItem]


class N8nStatusRead(ORMModel):
    enabled: bool
    webhook_configured: bool
    secret_configured: bool
    last_test_status: str | None = None
    last_test_at: datetime | None = None


class N8nTestPayload(ORMModel):
    recipient_email: str
    recipient_name: str | None = None
    subject: str = "[ClubAgent] n8n 테스트 메일"
    body: str = "n8n Gmail 발송 테스트입니다."
    target_url: str | None = None


class N8nTestResult(ORMModel):
    ok: bool
    status: str
    detail: str | None = None
