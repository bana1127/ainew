from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.llm_service import LLMService, ActivityReportGenerationPayload
from app.agents.file_parser_agent import FileParserAgent, FileParserResult
from app.agents.post_agent import PostAgent, PostAgentResult
from app.agents.publisher_agent import PublisherAgent


@dataclass
class OrchestratorInput:
    category_id: UUID
    title: str
    category_name: str | None = None
    report_template: str | None = None
    reference_content: str | None = None
    activity_date: str | None = None  # ISO date string
    location: str | None = None
    input_text: str | None = None
    participant_names: list[str] = field(default_factory=list)
    file_ids: list[UUID] = field(default_factory=list)
    activity_report_id: UUID | None = None
    save_to_db: bool = True


@dataclass
class OrchestratorOutput:
    title: str
    summary: str
    content: str
    missing_fields: list[str]
    confidence: float
    model: str
    saved: bool
    activity_report_id: UUID | None


class ActivityReportOrchestrator:
    def __init__(self, db: Session):
        self.db = db
        self.llm = LLMService(
            api_key=settings.OPENAI_API_KEY,
            model=settings.OPENAI_MODEL,
            mock_mode=settings.OPENAI_MOCK_MODE,
        )

    def run(self, input_data: OrchestratorInput) -> OrchestratorOutput:
        # 1. FileParser Agent: parse file metadata
        file_result = FileParserAgent(self.db).parse(input_data.file_ids)

        # 2. Post Agent: generate report using LLM
        payload = ActivityReportGenerationPayload(
            category_name=input_data.category_name,
            report_template=input_data.report_template,
            title=input_data.title,
            activity_date=input_data.activity_date,
            location=input_data.location,
            participant_names=input_data.participant_names,
            input_text=input_data.input_text,
            reference_content=input_data.reference_content,
            file_names=file_result.file_names,
        )
        post_result = PostAgent(self.llm).generate(payload)

        # 3. Publisher Agent: save to DB if requested
        saved = False
        activity_report_id = input_data.activity_report_id
        if input_data.save_to_db:
            activity_report_id, saved = PublisherAgent(self.db).publish(
                activity_report_id=input_data.activity_report_id,
                category_id=input_data.category_id,
                title=post_result.title,
                activity_date=input_data.activity_date,
                location=input_data.location,
                input_text=input_data.input_text,
                generated_content=post_result.content,
            )

        return OrchestratorOutput(
            title=post_result.title,
            summary=post_result.summary,
            content=post_result.content,
            missing_fields=post_result.missing_fields,
            confidence=post_result.confidence,
            model=post_result.model,
            saved=saved,
            activity_report_id=activity_report_id,
        )
