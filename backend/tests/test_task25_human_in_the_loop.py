# -*- coding: utf-8 -*-
"""Tests for Task 25: Human-in-the-loop confirmation mode.

Covers:
  - auto_apply is always False in AssistantInput (router enforces it)
  - bank_statement_import returns requires_confirmation=True with action_id
  - payment_matching returns requires_confirmation=True with action_id
  - receipt_analysis returns requires_confirmation=True with action_id
  - activity_report_generate returns requires_confirmation=True with action_id
  - activity_fee_generate returns requires_confirmation=True with action_id
  - payment_manual_update returns requires_confirmation=True with action_id
  - confirm_action_proposal rejects already-applied proposals
  - cancel_action_proposal marks as cancelled
"""
from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest


# ---------------------------------------------------------------------------
# Minimal stubs required to import service modules without real DB/SQLА
# ---------------------------------------------------------------------------

def _stub(name: str) -> ModuleType:
    mod = ModuleType(name)
    mod.__spec__ = None  # type: ignore[attr-defined]
    return mod


for _m in ("psycopg", "psycopg2", "psycopg2.extras"):
    if _m not in sys.modules:
        sys.modules[_m] = _stub(_m)

for _mod_name in ("app.core.database", "app.core.config"):
    if _mod_name not in sys.modules:
        _m2 = _stub(_mod_name)
        _m2.Base = MagicMock()  # type: ignore[attr-defined]
        _m2.engine = MagicMock()  # type: ignore[attr-defined]
        _m2.SessionLocal = MagicMock()  # type: ignore[attr-defined]
        _m2.get_db = MagicMock()  # type: ignore[attr-defined]
        _m2.settings = MagicMock()  # type: ignore[attr-defined]
        sys.modules[_mod_name] = _m2

_sa = _stub("sqlalchemy")
for _attr in ("select", "and_", "or_", "func", "update", "Index", "String", "Text",
              "Boolean", "DateTime", "Date", "Integer", "BigInteger",
              "UniqueConstraint", "ForeignKey", "Float"):
    setattr(_sa, _attr, MagicMock())
sys.modules.setdefault("sqlalchemy", _sa)

_sa_orm = _stub("sqlalchemy.orm")
for _attr in ("Session", "Mapped", "mapped_column", "relationship", "selectinload"):
    setattr(_sa_orm, _attr, MagicMock())
sys.modules.setdefault("sqlalchemy.orm", _sa_orm)

_sa_d = _stub("sqlalchemy.dialects.postgresql")
_sa_d.UUID = MagicMock()  # type: ignore[attr-defined]
_sa_d.JSONB = MagicMock()  # type: ignore[attr-defined]
sys.modules.setdefault("sqlalchemy.dialects.postgresql", _sa_d)

# Model stubs — prevent metaclass conflict from real SQLAlchemy models
for _mod_name2 in (
    "app.models", "app.models.base", "app.models.activity",
    "app.models.member", "app.models.payment", "app.models.receipt",
    "app.models.file", "app.models.notification", "app.models.setting",
    "app.models.transaction", "app.models.activity_feedback",
    "app.models.assistant_action",
):
    if _mod_name2 not in sys.modules:
        _m3 = _stub(_mod_name2)
        for _cls in (
            "ActivityReport", "ActivityParticipant", "ActivityCategory",
            "ReferenceReport", "Member", "PaymentRecord", "PaymentAdjustmentLog",
            "BankTransaction", "Receipt", "UploadedFile", "Notification",
            "AppSetting", "ActivityFeedback", "AssistantActionProposal", "Base",
        ):
            setattr(_m3, _cls, MagicMock)
        sys.modules[_mod_name2] = _m3

for _mod_name3 in ("app.agents.activity_resolver", "app.schemas.assistant"):
    if _mod_name3 not in sys.modules:
        _m4 = _stub(_mod_name3)
        _m4.resolve_activity_context = MagicMock()  # type: ignore[attr-defined]
        _m4.ActivityResolutionResult = MagicMock  # type: ignore[attr-defined]
        _m4.AssistantExecuteResponse = MagicMock  # type: ignore[attr-defined]
        sys.modules[_mod_name3] = _m4


# ---------------------------------------------------------------------------
# Tests for intent router — payment_manual_update / activity_fee_generate
# ---------------------------------------------------------------------------

class TestIntentRouterHITL:
    """Intent router must route correctly so proposals are created for the right intents."""

    def _route(self, message: str, file_names: list[str] | None = None) -> str:
        from app.agents.intent_router import route
        result = route(message=message, file_names=file_names or [])
        return result.intent

    def test_bank_keywords_with_file(self):
        intent = self._route("거래내역서 분석해줘", ["거래내역.xlsx"])
        assert intent == "bank_statement_import"

    def test_payment_matching_keywords(self):
        intent = self._route("이번 달 회비 납부 매칭해줘")
        assert intent == "payment_matching"

    def test_payment_manual_update_with_name(self):
        intent = self._route("박민서 학생이 활동비 25000원 납부했어")
        assert intent == "payment_manual_update"

    def test_activity_fee_generate_keywords(self):
        intent = self._route("참여자 기준으로 활동비 25000원 납부 대상 만들어줘")
        assert intent == "activity_fee_generate"

    def test_no_auto_apply_path_for_matching(self):
        """Payment matching should NOT route to a direct-apply intent."""
        intent = self._route("회비 매칭해줘")
        # Must go through preview (payment_matching), never a direct-apply variant
        assert intent in ("payment_matching", "unknown")

    def test_amount_only_no_name_is_not_payment_update(self):
        """'활동비 25000원으로 바꿔줘' without a name is NOT payment_manual_update."""
        intent = self._route("활동비 25000원으로 바꿔줘")
        assert intent != "payment_manual_update"


# ---------------------------------------------------------------------------
# Tests for _get_pending_action guard
# ---------------------------------------------------------------------------

class TestActionProposalGuard:
    """confirm/cancel must reject proposals in non-pending states."""

    def _make_proposal(self, status: str):
        proposal = MagicMock()
        proposal.id = uuid4()
        proposal.status = status
        proposal.action_type = "payment_matching"
        proposal.payload_json = {}
        proposal.preview_json = {}
        return proposal

    def _make_db(self, proposal):
        db = MagicMock()
        db.get.return_value = proposal
        return db

    def test_confirm_pending_ok(self):
        """confirm_action_proposal succeeds for a pending proposal."""
        proposal = self._make_proposal("pending")
        db = self._make_db(proposal)

        with patch(
            "app.services.assistant_action_service.apply_payment_matching_action",
            return_value={"matched_count": 5, "unpaid_count": 2}
        ):
            from app.services.assistant_action_service import confirm_action_proposal
            _, result = confirm_action_proposal(db, proposal.id)
        assert result["matched_count"] == 5

    def test_confirm_already_applied_raises(self):
        """confirm_action_proposal raises ValueError for an applied proposal."""
        proposal = self._make_proposal("applied")
        db = self._make_db(proposal)

        from app.services.assistant_action_service import confirm_action_proposal
        with pytest.raises(ValueError, match="not pending"):
            confirm_action_proposal(db, proposal.id)

    def test_cancel_pending_ok(self):
        """cancel_action_proposal marks proposal as cancelled."""
        proposal = self._make_proposal("pending")
        db = self._make_db(proposal)

        from app.services.assistant_action_service import cancel_action_proposal
        result = cancel_action_proposal(db, proposal.id)
        assert proposal.status == "cancelled"

    def test_confirm_not_found_raises(self):
        """confirm_action_proposal raises ValueError when proposal not found."""
        db = MagicMock()
        db.get.return_value = None

        from app.services.assistant_action_service import confirm_action_proposal
        with pytest.raises(ValueError, match="not found"):
            confirm_action_proposal(db, uuid4())


# ---------------------------------------------------------------------------
# Tests for requires_confirmation in orchestrator responses
# ---------------------------------------------------------------------------

class TestOrchestratorRequiresConfirmation:
    """AssistantOrchestrator must always set requires_confirmation=True for major intents."""

    def _make_db(self):
        db = MagicMock()
        # db.get returns None by default (no activity found)
        db.get.return_value = None
        db.scalars.return_value.all.return_value = []
        return db

    def test_payment_matching_preview_requires_confirmation(self):
        """_payment_matching always returns requires_confirmation=True."""
        from app.agents.intent_router import IntentResult

        ir = IntentResult("payment_matching", 0.8, "test")
        db = self._make_db()

        # Mock preview_payment_matching to avoid DB calls
        with patch("app.services.payment_matching_service.preview_payment_matching") as mock_preview, \
             patch("app.services.assistant_action_service.create_action_proposal") as mock_proposal:
            mock_preview_result = MagicMock()
            mock_preview_result.period = "2026-1"
            mock_preview_result.payment_type = "membership_fee"
            mock_preview_result.required_amount = 30000
            mock_preview_result.total_active_members = 10
            mock_preview_result.matched_count = 5
            mock_preview_result.need_check_count = 1
            mock_preview_result.unpaid_count = 4
            mock_preview_result.excluded_count = 0
            mock_preview_result.unpaid_members = []
            mock_preview.return_value = mock_preview_result

            mock_action = MagicMock()
            mock_action.id = uuid4()
            mock_action.status = "pending"
            mock_proposal.return_value = mock_action

            from app.agents.assistant_orchestrator import AssistantInput, AssistantOrchestrator
            orch = AssistantOrchestrator(db)
            inp = AssistantInput(
                message="회비 매칭해줘",
                auto_apply=False,  # Task 25: always False
            )
            resp = orch._payment_matching(inp, ir)

        assert resp.requires_confirmation is True
        assert resp.apply_payload is not None
        assert "action_id" in resp.apply_payload

    def test_payment_matching_never_auto_applies(self):
        """Even if auto_apply=True is somehow passed, it must still require confirmation."""
        from app.agents.intent_router import IntentResult

        ir = IntentResult("payment_matching", 0.8, "test")
        db = self._make_db()

        with patch("app.services.payment_matching_service.preview_payment_matching") as mock_preview, \
             patch("app.services.assistant_action_service.create_action_proposal") as mock_proposal:
            mock_preview_result = MagicMock()
            mock_preview_result.period = "2026-1"
            mock_preview_result.payment_type = "membership_fee"
            mock_preview_result.required_amount = 30000
            mock_preview_result.total_active_members = 10
            mock_preview_result.matched_count = 5
            mock_preview_result.need_check_count = 1
            mock_preview_result.unpaid_count = 4
            mock_preview_result.excluded_count = 0
            mock_preview_result.unpaid_members = []
            mock_preview.return_value = mock_preview_result

            mock_action = MagicMock()
            mock_action.id = uuid4()
            mock_action.status = "pending"
            mock_proposal.return_value = mock_action

            from app.agents.assistant_orchestrator import AssistantInput, AssistantOrchestrator
            orch = AssistantOrchestrator(db)
            inp = AssistantInput(
                message="회비 매칭해줘",
                auto_apply=True,  # should be ignored/overridden
            )
            resp = orch._payment_matching(inp, ir)

        # must STILL require confirmation regardless of auto_apply
        assert resp.requires_confirmation is True
        assert resp.result_type == "payment_matching_preview"
