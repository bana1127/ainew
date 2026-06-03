import os
import sys
from types import ModuleType
from unittest.mock import MagicMock


def _stub_module(name: str) -> ModuleType:
    mod = ModuleType(name)
    mod.__spec__ = None  # type: ignore[attr-defined]
    return mod


for _mod_name in ("psycopg", "psycopg2", "psycopg2.extras"):
    sys.modules.setdefault(_mod_name, _stub_module(_mod_name))

_db_mod = _stub_module("app.core.database")
_db_mod.Base = MagicMock()  # type: ignore[attr-defined]
_db_mod.engine = MagicMock()  # type: ignore[attr-defined]
_db_mod.SessionLocal = MagicMock()  # type: ignore[attr-defined]
sys.modules.setdefault("app.core.database", _db_mod)

_cfg_mod = _stub_module("app.core.config")
_cfg_mod.settings = MagicMock()  # type: ignore[attr-defined]
sys.modules.setdefault("app.core.config", _cfg_mod)

_models_mod = _stub_module("app.models")
_models_mod.BankTransaction = MagicMock()  # type: ignore[attr-defined]
_models_mod.Member = MagicMock()  # type: ignore[attr-defined]
_models_mod.PaymentRecord = MagicMock()  # type: ignore[attr-defined]
sys.modules.setdefault("app.models", _models_mod)

_setting_mod = _stub_module("app.models.setting")
_setting_mod.AppSetting = MagicMock()  # type: ignore[attr-defined]
sys.modules.setdefault("app.models.setting", _setting_mod)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.payment_matching_service import evaluate_membership_fee_match_gate  # noqa: E402


def gate(**kwargs):
    defaults = {
        "deposit_amount": 10000,
        "required_amount": 10000,
        "has_payment_record": True,
        "record_status": "unpaid",
        "existing_paid_amount": 0,
        "name_status": "matched",
        "transaction_already_matched": False,
    }
    defaults.update(kwargs)
    return evaluate_membership_fee_match_gate(**defaults)


def test_required_15000_deposit_10000_is_partial_amount_mismatch():
    status, amount_status, auto_match = gate(required_amount=15000, deposit_amount=10000)

    assert status == "need_check"
    assert amount_status == "amount_mismatch_partial"
    assert auto_match is False


def test_required_10000_deposit_15000_is_overpaid_amount_mismatch():
    status, amount_status, auto_match = gate(required_amount=10000, deposit_amount=15000)

    assert status == "need_check"
    assert amount_status == "amount_mismatch_overpaid"
    assert auto_match is False


def test_executive_required_zero_deposit_is_review_not_auto_match():
    status, amount_status, auto_match = gate(required_amount=0, deposit_amount=10000)

    assert status == "need_check"
    assert amount_status == "amount_mismatch_overpaid"
    assert auto_match is False


def test_missing_payment_record_blocks_auto_match():
    status, amount_status, auto_match = gate(has_payment_record=False, required_amount=None)

    assert status == "need_check"
    assert amount_status == "missing_payment_record"
    assert auto_match is False


def test_confirm_time_required_amount_change_blocks_previous_preview_match():
    preview = gate(required_amount=10000, deposit_amount=10000)
    confirm = gate(required_amount=15000, deposit_amount=10000)

    assert preview == ("matched", "exact_amount", True)
    assert confirm == ("need_check", "amount_mismatch_partial", False)
