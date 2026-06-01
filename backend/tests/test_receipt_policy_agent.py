"""Unit tests for PolicyAgent - audit rule checks."""
import sys
import os
from pathlib import Path
import pytest

# Stub DB modules so we can import policy_agent without a live DB
from types import ModuleType

def _make_stub(name):
    m = ModuleType(name)
    m.__spec__ = None
    return m

for mod_name in ("sqlalchemy", "sqlalchemy.orm", "psycopg", "psycopg2"):
    if mod_name not in sys.modules:
        sys.modules[mod_name] = _make_stub(mod_name)
from unittest.mock import MagicMock
for m_name in ("app.core.database", "app.core.config", "app.models", "app.models.base"):
    stub = _make_stub(m_name)
    stub.Base = MagicMock(); stub.settings = MagicMock()
    sys.modules[m_name] = stub

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.agents.policy_agent import PolicyAgent

class TestPolicyAgent:
    def test_card_is_valid(self):
        result = PolicyAgent().check("card")
        assert result.evidence_status == "valid"
        assert result.need_check is False

    def test_online_card_is_valid(self):
        result = PolicyAgent().check("online_card")
        assert result.evidence_status == "valid"
        assert result.need_check is False

    def test_transfer_student_is_need_check(self):
        result = PolicyAgent().check("transfer_student")
        assert result.evidence_status == "need_check"
        assert result.need_check is True

    def test_transfer_company_is_need_check(self):
        result = PolicyAgent().check("transfer_company")
        assert result.evidence_status == "need_check"
        assert result.need_check is True

    def test_cash_withdrawal_is_invalid(self):
        result = PolicyAgent().check("cash_withdrawal")
        assert result.evidence_status == "invalid"
        assert result.need_check is True

    def test_personal_card_reimbursement_is_invalid(self):
        result = PolicyAgent().check("personal_card_reimbursement")
        assert result.evidence_status == "invalid"
        assert result.need_check is True

    def test_recurring_payment_is_need_check(self):
        result = PolicyAgent().check("recurring_payment")
        assert result.evidence_status == "need_check"
        assert result.need_check is True

    def test_unknown_is_need_check(self):
        result = PolicyAgent().check("unknown")
        assert result.evidence_status == "need_check"
        assert result.need_check is True

    def test_nonexistent_key_fallback_to_unknown(self):
        result = PolicyAgent().check("nonexistent_method")
        assert result.evidence_status == "need_check"
        assert result.rule_key == "unknown"

    def test_rule_key_matches_input(self):
        result = PolicyAgent().check("card")
        assert result.rule_key == "card"

    def test_required_evidence_for_card(self):
        result = PolicyAgent().check("card")
        assert "receipt" in result.required_evidence

    def test_reason_is_nonempty(self):
        result = PolicyAgent().check("transfer_student")
        assert len(result.reason) > 0
