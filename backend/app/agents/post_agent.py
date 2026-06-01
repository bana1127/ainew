from __future__ import annotations
from dataclasses import dataclass, field
from app.services.llm_service import LLMService, ActivityReportGenerationPayload


@dataclass
class PostAgentResult:
    title: str
    summary: str
    content: str
    missing_fields: list[str]
    confidence: float
    model: str


class PostAgent:
    def __init__(self, llm: LLMService):
        self.llm = llm

    def generate(self, payload: ActivityReportGenerationPayload) -> PostAgentResult:
        result = self.llm.generate_activity_report(payload)
        return PostAgentResult(
            title=result.get("title", payload.title),
            summary=result.get("summary", ""),
            content=result.get("content", ""),
            missing_fields=result.get("missing_fields", []),
            confidence=result.get("confidence", 0.0),
            model=result.get("model", "unknown"),
        )
