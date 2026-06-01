from __future__ import annotations
from app.services.llm_service import LLMService, ReceiptAnalysisPayload


class ReceiptAgent:
    def __init__(self, llm: LLMService):
        self.llm = llm

    def extract(self, payload: ReceiptAnalysisPayload) -> dict:
        """Call LLMService to extract receipt data. Returns a dict with all extracted fields."""
        return self.llm.analyze_receipt(payload)
