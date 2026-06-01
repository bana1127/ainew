from __future__ import annotations
import json
from dataclasses import dataclass, field
from pathlib import Path

AUDIT_RULES_PATH = Path(__file__).resolve().parents[1] / "data" / "audit_rules.json"
_RULES: dict | None = None


def _load_rules() -> dict:
    global _RULES
    if _RULES is None:
        with AUDIT_RULES_PATH.open(encoding="utf-8") as f:
            _RULES = json.load(f)
    return _RULES


@dataclass
class PolicyResult:
    evidence_status: str
    need_check: bool
    required_evidence: list[str]
    reason: str
    rule_key: str


class PolicyAgent:
    def check(self, payment_method: str) -> PolicyResult:
        rules = _load_rules()
        rule = rules.get(payment_method, rules.get("unknown"))
        rule_key = payment_method if payment_method in rules else "unknown"

        status = rule.get("status", "need_check")
        message = rule.get("message", "감사 규정 확인이 필요합니다.")
        required_evidence = rule.get("required_evidence", [])

        if status == "allowed":
            evidence_status = "valid"
            need_check = False
        elif status == "not_allowed":
            evidence_status = "invalid"
            need_check = True
        else:
            evidence_status = "need_check"
            need_check = True

        return PolicyResult(
            evidence_status=evidence_status,
            need_check=need_check,
            required_evidence=required_evidence,
            reason=message,
            rule_key=rule_key,
        )
