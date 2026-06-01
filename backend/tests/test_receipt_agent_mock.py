"""Unit tests for receipt analysis in mock mode."""
import sys
import os
from types import ModuleType
from unittest.mock import MagicMock
import pytest

def _make_stub(name):
    m = ModuleType(name)
    m.__spec__ = None
    return m

for mod_name in ("psycopg", "psycopg2", "psycopg2.extras"):
    if mod_name not in sys.modules:
        sys.modules[mod_name] = _make_stub(mod_name)

db_mod = _make_stub("app.core.database")
db_mod.Base = MagicMock(); db_mod.engine = MagicMock(); db_mod.SessionLocal = MagicMock()
sys.modules["app.core.database"] = db_mod

cfg_mod = _make_stub("app.core.config")
mock_settings = MagicMock()
mock_settings.OPENAI_API_KEY = None; mock_settings.OPENAI_MODEL = "gpt-4.1-mini"
mock_settings.OPENAI_MOCK_MODE = True; mock_settings.OPENAI_VISION_MODEL = ""
cfg_mod.settings = mock_settings
sys.modules["app.core.config"] = cfg_mod

for m_name in ["app.models", "app.models.file", "app.models.receipt",
               "app.models.activity", "app.models.base"]:
    stub = _make_stub(m_name)
    stub.UploadedFile = MagicMock(); stub.Receipt = MagicMock()
    stub.ActivityReport = MagicMock(); stub.Base = MagicMock()
    sys.modules[m_name] = stub

for m_name in ["sqlalchemy", "sqlalchemy.orm"]:
    if m_name not in sys.modules:
        stub = _make_stub(m_name); stub.select = MagicMock(); stub.Session = MagicMock()
        sys.modules[m_name] = stub

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.llm_service import LLMService, ReceiptAnalysisPayload
from app.agents.classifier_agent import ClassifierAgent

def make_llm():
    return LLMService(api_key=None, model="mock", mock_mode=True)


class TestLLMServiceReceiptMock:
    def test_mock_returns_dict(self):
        llm = make_llm()
        result = llm.analyze_receipt(ReceiptAnalysisPayload(file_name="receipt.jpg"))
        assert isinstance(result, dict)
        assert "amount" in result
        assert "payment_method" in result

    def test_mock_no_api_key_needed(self):
        llm = LLMService(api_key=None, model="mock", mock_mode=True)
        result = llm.analyze_receipt(ReceiptAnalysisPayload(file_name="card_5000.jpg"))
        assert result["payment_method"] == "card"

    def test_real_mode_no_api_key_raises(self):
        llm = LLMService(api_key=None, model="gpt-4.1-mini", mock_mode=False)
        with pytest.raises(ValueError):
            llm.analyze_receipt(ReceiptAnalysisPayload(file_name="receipt.jpg"))

    def test_mock_filename_hint_card(self):
        llm = make_llm()
        result = llm.analyze_receipt(ReceiptAnalysisPayload(file_name="receipt_card_50700.jpg"))
        assert result["payment_method"] == "card"
        assert result["amount"] == 50700

    def test_mock_filename_hint_transfer_student(self):
        llm = make_llm()
        result = llm.analyze_receipt(ReceiptAnalysisPayload(file_name="transfer_student_30000.png"))
        assert result["payment_method"] == "transfer_student"
        assert result["amount"] == 30000

    def test_mock_filename_hint_online(self):
        llm = make_llm()
        result = llm.analyze_receipt(ReceiptAnalysisPayload(file_name="online_12000.png"))
        assert result["payment_method"] == "online_card"
        assert result["amount"] == 12000

    def test_mock_manual_override_payment_method(self):
        llm = make_llm()
        result = llm.analyze_receipt(ReceiptAnalysisPayload(
            file_name="receipt.jpg",
            manual_payment_method="transfer_company"
        ))
        assert result["payment_method"] == "transfer_company"

    def test_mock_confidence_is_float(self):
        llm = make_llm()
        result = llm.analyze_receipt(ReceiptAnalysisPayload(file_name="receipt.jpg"))
        assert isinstance(result["confidence"], float)
        assert 0.0 <= result["confidence"] <= 1.0


class TestClassifierAgent:
    def test_valid_payment_method_kept(self):
        agent = ClassifierAgent()
        assert agent.classify("card", None) == "card"

    def test_manual_override_takes_priority(self):
        agent = ClassifierAgent()
        assert agent.classify("unknown", "card") == "card"

    def test_invalid_method_becomes_unknown(self):
        agent = ClassifierAgent()
        assert agent.classify("invalid_method", None) == "unknown"

    def test_manual_category_takes_priority(self):
        agent = ClassifierAgent()
        assert agent.classify_category("기타", "간식비") == "간식비"

    def test_extracted_category_used_when_no_manual(self):
        agent = ClassifierAgent()
        assert agent.classify_category("간식비", None) == "간식비"
