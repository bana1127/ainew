from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from uuid import UUID
from sqlalchemy.orm import Session
from app.core.config import settings
from app.services.llm_service import LLMService, ReceiptAnalysisPayload
from app.agents.file_parser_agent import FileParserAgent
from app.agents.receipt_agent import ReceiptAgent
from app.agents.classifier_agent import ClassifierAgent
from app.agents.policy_agent import PolicyAgent, PolicyResult
from app.agents.budget_agent import BudgetAgent


@dataclass
class ReceiptOrchestratorInput:
    file_id: UUID
    file_path: Path | None  # absolute path on disk
    file_name: str
    mime_type: str | None
    activity_report_id: UUID | None = None
    save_to_db: bool = True
    manual_payment_method: str | None = None
    manual_category: str | None = None


@dataclass
class ExtractedData:
    receipt_date: str | None
    store_name: str | None
    amount: int
    payment_method: str
    category: str | None
    raw_text: str | None
    confidence: float


@dataclass
class PolicyData:
    evidence_status: str
    need_check: bool
    required_evidence: list[str]
    reason: str
    rule_key: str


@dataclass
class ReceiptOrchestratorOutput:
    receipt_id: UUID | None
    file_id: UUID
    activity_report_id: UUID | None
    extracted: ExtractedData
    policy: PolicyData
    saved: bool
    model: str


class ReceiptAnalysisOrchestrator:
    def __init__(self, db: Session):
        self.db = db
        self.llm = LLMService(
            api_key=settings.OPENAI_API_KEY,
            model=settings.OPENAI_MODEL,
            mock_mode=settings.OPENAI_MOCK_MODE,
            vision_model=settings.OPENAI_VISION_MODEL,
        )

    def run(self, input_data: ReceiptOrchestratorInput) -> ReceiptOrchestratorOutput:
        # 1. FileParser: verify file metadata
        file_info = FileParserAgent(self.db).parse_receipt_file(input_data.file_id)

        # 2. Receipt Agent: extract receipt data using LLM
        payload = ReceiptAnalysisPayload(
            file_name=input_data.file_name,
            file_path=str(input_data.file_path) if input_data.file_path else None,
            mime_type=input_data.mime_type,
            manual_payment_method=input_data.manual_payment_method,
            manual_category=input_data.manual_category,
        )
        extracted_dict = ReceiptAgent(self.llm).extract(payload)

        # 3. Classifier: override with manual inputs if provided
        payment_method = ClassifierAgent().classify(
            extracted_dict.get("payment_method", "unknown"),
            input_data.manual_payment_method,
        )
        category = ClassifierAgent().classify_category(
            extracted_dict.get("category"),
            input_data.manual_category,
        )
        extracted_dict["payment_method"] = payment_method
        extracted_dict["category"] = category

        # 4. Policy Agent: check against audit rules
        policy = PolicyAgent().check(payment_method)

        # 5. Budget Agent: minimal validation
        amount = extracted_dict.get("amount", 0)
        budget_note = BudgetAgent().validate(
            amount=amount,
            activity_report_id=input_data.activity_report_id,
        )
        if budget_note:
            policy.reason = policy.reason + f" {budget_note}"

        # 6. Publisher Agent: save to receipts table if requested
        receipt_id: UUID | None = None
        saved = False
        if input_data.save_to_db:
            from app.agents.publisher_agent import PublisherAgent
            receipt_id, saved = PublisherAgent(self.db).publish_receipt(
                file_id=input_data.file_id,
                activity_report_id=input_data.activity_report_id,
                extracted=extracted_dict,
                evidence_status=policy.evidence_status,
                need_check=policy.need_check,
                reason=policy.reason,
            )

        extracted = ExtractedData(
            receipt_date=extracted_dict.get("receipt_date"),
            store_name=extracted_dict.get("store_name"),
            amount=extracted_dict.get("amount", 0),
            payment_method=payment_method,
            category=category,
            raw_text=extracted_dict.get("raw_text"),
            confidence=extracted_dict.get("confidence", 0.0),
        )
        policy_data = PolicyData(
            evidence_status=policy.evidence_status,
            need_check=policy.need_check,
            required_evidence=policy.required_evidence,
            reason=policy.reason,
            rule_key=policy.rule_key,
        )

        model_str = "mock" if settings.OPENAI_MOCK_MODE else (settings.OPENAI_VISION_MODEL or settings.OPENAI_MODEL)

        return ReceiptOrchestratorOutput(
            receipt_id=receipt_id,
            file_id=input_data.file_id,
            activity_report_id=input_data.activity_report_id,
            extracted=extracted,
            policy=policy_data,
            saved=saved,
            model=model_str,
        )
