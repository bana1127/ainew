"""Shared payment status calculation utilities (Task 40).

Single source of truth for computing payment status from amounts.
Used by: dashboard, budget, payments, activity detail, chatbot, audit preview.

Rules (shared for both membership_fee and activity_fee):
  required == 0               → exempt
  paid == 0                   → unpaid
  0 < paid < required         → partial
  paid == required            → paid
  paid > required             → overpaid

need_check is a MANUALLY assigned state, NOT computed from amounts.
It is only used when:
  - amount mismatch detected during matching
  - duplicate candidate detected
  - manager explicitly sets it
"""
from __future__ import annotations


def compute_status(paid: int, required: int) -> str:
    """Compute payment status from paid and required amounts.

    This function must be used wherever payment status is computed from amounts
    to guarantee consistency across the app.
    """
    required = max(0, required)
    paid = max(0, paid)

    if required == 0:
        return "exempt"
    if paid == 0:
        return "unpaid"
    if paid < required:
        return "partial"
    if paid == required:
        return "paid"
    return "overpaid"


def is_effectively_paid(paid: int, required: int, status: str) -> bool:
    """Return True if a payment record should be considered fully settled.

    A record is fully paid if:
    - paid == required (regardless of stored status)
    - status is 'paid' or 'exempt'
    """
    if required <= 0:
        return True
    return paid >= required or status in ("paid", "exempt")


def status_label(status: str) -> str:
    """Human-readable Korean label for a payment status."""
    labels = {
        "unpaid": "미납",
        "partial": "부분 납부",
        "paid": "납부 완료",
        "overpaid": "초과 납부",
        "need_check": "확인 필요",
        "exempt": "면제",
        "cancelled": "취소",
    }
    return labels.get(status, status)


def severity_for_status(status: str) -> str:
    """Return a CSS-token severity level for a payment status."""
    if status in ("unpaid", "need_check"):
        return "danger"
    if status == "partial":
        return "warning"
    if status in ("paid", "exempt"):
        return "success"
    return "neutral"
