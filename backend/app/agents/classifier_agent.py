from __future__ import annotations

VALID_PAYMENT_METHODS = {
    "card", "online_card", "transfer_student", "transfer_company",
    "cash_withdrawal", "personal_card_reimbursement", "recurring_payment", "unknown",
}


class ClassifierAgent:
    def classify(self, extracted_payment_method: str, manual_override: str | None) -> str:
        """
        Override extracted payment_method with manual input if provided.
        Normalize to a valid value, defaulting to 'unknown'.
        """
        if manual_override and manual_override in VALID_PAYMENT_METHODS:
            return manual_override
        if extracted_payment_method in VALID_PAYMENT_METHODS:
            return extracted_payment_method
        return "unknown"

    def classify_category(self, extracted_category: str | None, manual_override: str | None) -> str | None:
        """Use manual category if provided, otherwise use extracted."""
        if manual_override and manual_override.strip():
            return manual_override.strip()
        return extracted_category
