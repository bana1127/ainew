from __future__ import annotations
from uuid import UUID


class BudgetAgent:
    """
    Minimal budget validation for Task 8.
    Full budget/balance calculation is deferred to a future Task.
    """

    def validate(
        self,
        amount: int,
        activity_report_id: UUID | None,
    ) -> str:
        """
        Returns a supplementary note string (empty if no issue).
        TODO(Task 9+): Add actual budget balance check against activity budget.
        """
        if amount <= 0:
            return "금액이 0 이하입니다. 금액을 확인해 주세요."
        if activity_report_id is None:
            return ""
        # TODO(Task 9+): Verify this amount against the activity's remaining budget
        return ""
