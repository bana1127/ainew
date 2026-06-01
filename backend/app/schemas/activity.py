from datetime import date, datetime
from typing import Any
from uuid import UUID

from app.schemas.common import ORMModel


class ActivityCategoryBase(ORMModel):
    name: str
    description: str | None = None
    required_fields_json: dict[str, Any] | None = None
    report_template: str | None = None


class ActivityCategoryCreate(ActivityCategoryBase):
    pass


class ActivityCategoryUpdate(ORMModel):
    name: str | None = None
    description: str | None = None
    required_fields_json: dict[str, Any] | None = None
    report_template: str | None = None


class ActivityCategoryRead(ActivityCategoryBase):
    id: UUID
    created_at: datetime
    updated_at: datetime


class ReferenceReportBase(ORMModel):
    category_id: UUID | None = None
    title: str
    content: str
    tags: list[str] | None = None


class ReferenceReportCreate(ReferenceReportBase):
    pass


class ReferenceReportUpdate(ORMModel):
    category_id: UUID | None = None
    title: str | None = None
    content: str | None = None
    tags: list[str] | None = None


class ReferenceReportRead(ReferenceReportBase):
    id: UUID
    created_at: datetime
    updated_at: datetime


class ActivityReportBase(ORMModel):
    category_id: UUID | None = None
    title: str
    activity_date: date | None = None
    location: str | None = None
    input_text: str | None = None
    generated_content: str | None = None
    final_content: str | None = None
    status: str = "draft"


class ActivityReportCreate(ActivityReportBase):
    pass


class ActivityReportUpdate(ORMModel):
    category_id: UUID | None = None
    title: str | None = None
    activity_date: date | None = None
    location: str | None = None
    input_text: str | None = None
    generated_content: str | None = None
    final_content: str | None = None
    status: str | None = None


class ActivityReportRead(ActivityReportBase):
    id: UUID
    created_at: datetime
    updated_at: datetime


class ActivityParticipantBase(ORMModel):
    activity_report_id: UUID
    member_id: UUID
    role: str | None = None


class ActivityParticipantCreate(ActivityParticipantBase):
    pass


class ActivityParticipantUpdate(ORMModel):
    role: str | None = None


class ActivityParticipantRead(ActivityParticipantBase):
    id: UUID
    created_at: datetime


class MemberRef(ORMModel):
    id: UUID
    name: str
    student_id: str | None = None


class ActivityParticipantWithMemberRead(ORMModel):
    id: UUID
    activity_report_id: UUID
    member_id: UUID
    role: str | None = None
    created_at: datetime
    member: MemberRef | None = None


class ParticipantItem(ORMModel):
    member_id: UUID
    role: str | None = None


class ParticipantsBulkUpdate(ORMModel):
    participants: list[ParticipantItem]

