"""Assistant Orchestrator — routes user requests to existing agents/services.

Task 17: Activity-aware orchestration.
- Activity Resolver runs before intent routing
- When activity context is linked, handlers connect results to the activity
- New handler: activity_fee_generate

Receives an intent from the IntentRouter and delegates to:
  - ReceiptAnalysisOrchestrator  (receipt_analysis)
  - bank_statement_parser        (bank_statement_import)
  - payment_matching_service     (payment_matching)
  - ActivityReportOrchestrator   (activity_report_generate)
  - activity_fee generator       (activity_fee_generate)
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from app.agents.activity_resolver import ActivityResolutionResult, resolve_activity_context
from app.agents.intent_router import IntentResult, route
from app.schemas.assistant import AssistantExecuteResponse

logger = logging.getLogger(__name__)

# detail_url mapping by result_type
DETAIL_URLS: dict[str, str] = {
    "receipt_analysis": "/receipts",
    "bank_statement_preview": "/transactions",
    "bank_statement_import_result": "/transactions",
    "payment_matching_preview": "/payments",
    "payment_matching_result": "/payments",
    "activity_report_draft": "/reports",
    "activity_fee_generation_result": "/payments?tab=activity_fee",
    "general_message": "/dashboard",
    "error": "/assistant",
}


@dataclass
class AssistantInput:
    message: str | None
    file_ids: list[UUID] = field(default_factory=list)
    file_names: list[str] = field(default_factory=list)
    file_paths: list[Path] = field(default_factory=list)
    mime_types: list[str | None] = field(default_factory=list)
    requested_intent: str = "auto"
    auto_apply: bool = False
    period: str = "2026-1"
    payment_type: str = "membership_fee"
    required_amount: int = 30000
    # Task 17: Activity context
    activity_id: UUID | None = None
    activity_mode: str = "auto"
    create_activity_if_missing: bool = False


def _build_activity_context_dict(res: ActivityResolutionResult) -> dict:
    d: dict = {
        "mode": res.mode,
        "confidence": res.confidence,
    }
    if res.activity_id:
        d["activity_id"] = res.activity_id
    if res.activity_title:
        d["activity_title"] = res.activity_title
    return d


def _build_candidates_list(res: ActivityResolutionResult) -> list[dict]:
    return [
        {
            "id": c.id,
            "title": c.title,
            "activity_date": c.activity_date,
            "location": c.location,
            "score": round(c.score, 3),
        }
        for c in res.candidates
    ]


class AssistantOrchestrator:
    def __init__(self, db: Session):
        self.db = db

    def run(self, inp: AssistantInput) -> AssistantExecuteResponse:
        # ── Step 1: Activity Resolver ──────────────────────────────────────
        activity_res = resolve_activity_context(
            db=self.db,
            message=inp.message,
            file_names=inp.file_names,
            activity_id=inp.activity_id,
            activity_mode=inp.activity_mode,
            create_activity_if_missing=inp.create_activity_if_missing,
        )

        # If resolver needs user confirmation, return early
        if activity_res.mode in ("needs_confirmation", "create_draft") and inp.activity_id is None:
            activity_context = _build_activity_context_dict(activity_res)
            candidates = _build_candidates_list(activity_res)

            if activity_res.mode == "create_draft":
                msg = "관련 활동을 찾지 못했습니다. 새 활동으로 생성할까요?"
                return AssistantExecuteResponse(
                    intent="unknown",
                    confidence=activity_res.confidence,
                    agent_flow=["Activity Resolver"],
                    result_type="activity_draft",
                    result={},
                    requires_confirmation=True,
                    message=msg,
                    activity_context=activity_context,
                    activity_candidates=candidates,
                    activity_draft=activity_res.draft,
                    detail_url="/activities",
                )
            else:
                msg = "연결할 활동 후보를 선택해 주세요." if candidates else "활동을 찾지 못했습니다."
                return AssistantExecuteResponse(
                    intent="unknown",
                    confidence=activity_res.confidence,
                    agent_flow=["Activity Resolver"],
                    result_type="activity_candidate",
                    result={},
                    requires_confirmation=True,
                    message=msg,
                    activity_context=activity_context,
                    activity_candidates=candidates,
                    detail_url="/activities",
                )

        # ── Step 2: Intent Router ──────────────────────────────────────────
        intent_result: IntentResult = route(
            message=inp.message,
            file_names=inp.file_names,
            requested_intent=inp.requested_intent,
        )
        intent = intent_result.intent

        # ── Step 3: Execute based on intent + activity context ─────────────
        activity_context = _build_activity_context_dict(activity_res)
        candidates = _build_candidates_list(activity_res)

        # Add "Activity Resolver" to agent flow prefix
        def with_resolver(flow: list[str]) -> list[str]:
            return ["Activity Resolver"] + flow if activity_res.mode != "none" else flow

        try:
            if intent == "activity_fee_generate":
                resp = self._activity_fee_generate(inp, intent_result, activity_res)
            elif intent == "receipt_analysis":
                resp = self._receipt_analysis(inp, intent_result, activity_res)
            elif intent == "bank_statement_import":
                resp = self._bank_statement(inp, intent_result)
            elif intent == "payment_matching":
                resp = self._payment_matching(inp, intent_result)
            elif intent == "activity_report_generate":
                resp = self._activity_report(inp, intent_result, activity_res)
            elif intent == "activity_link":
                resp = self._activity_link(inp, intent_result, activity_res)
            elif intent == "activity_create":
                resp = self._activity_create_prompt(inp, intent_result, activity_res)
            else:
                resp = self._unknown(inp, intent_result)

            # Attach activity context to all responses
            if activity_res.mode != "none":
                resp.activity_context = activity_context
                if candidates:
                    resp.activity_candidates = candidates
                if activity_res.draft:
                    resp.activity_draft = activity_res.draft
                # Prepend Activity Resolver to agent_flow
                if "Activity Resolver" not in resp.agent_flow:
                    resp.agent_flow = ["Activity Resolver"] + resp.agent_flow

            return resp

        except Exception as exc:
            logger.exception("AssistantOrchestrator error: %s", exc)
            return AssistantExecuteResponse(
                intent=intent,
                confidence=intent_result.confidence,
                agent_flow=["Activity Resolver", "AssistantOrchestrator"] if activity_res.mode != "none" else ["AssistantOrchestrator"],
                result_type="error",
                result={"error": str(exc)},
                requires_confirmation=False,
                message=f"처리 중 오류가 발생했습니다: {exc}",
                activity_context=activity_context if activity_res.mode != "none" else None,
                detail_url="/assistant",
            )

    # ------------------------------------------------------------------
    # receipt_analysis
    # ------------------------------------------------------------------

    def _receipt_analysis(
        self,
        inp: AssistantInput,
        ir: IntentResult,
        activity_res: ActivityResolutionResult,
    ) -> AssistantExecuteResponse:
        if not inp.file_ids:
            return AssistantExecuteResponse(
                intent="receipt_analysis",
                confidence=ir.confidence,
                agent_flow=["IntentRouter"],
                result_type="error",
                result={"error": "영수증 파일이 필요합니다."},
                requires_confirmation=False,
                message="영수증 이미지 파일을 첨부해 주세요.",
                detail_url="/receipts",
            )

        from app.agents.receipt_analysis_orchestrator import (
            ReceiptAnalysisOrchestrator,
            ReceiptOrchestratorInput,
        )

        file_id = inp.file_ids[0]
        file_path = inp.file_paths[0] if inp.file_paths else None
        file_name = inp.file_names[0] if inp.file_names else "receipt"
        mime_type = inp.mime_types[0] if inp.mime_types else None
        save = inp.auto_apply

        # If linked to an activity, save with activity_report_id
        linked_activity_id: UUID | None = None
        if activity_res.mode == "linked" and activity_res.activity_id:
            try:
                linked_activity_id = UUID(activity_res.activity_id)
            except (ValueError, AttributeError):
                pass

        orch_input = ReceiptOrchestratorInput(
            file_id=file_id,
            file_path=file_path,
            file_name=file_name,
            mime_type=mime_type,
            save_to_db=save,
            activity_report_id=linked_activity_id,
        )
        result = ReceiptAnalysisOrchestrator(self.db).run(orch_input)

        result_dict = {
            "receipt_id": str(result.receipt_id) if result.receipt_id else None,
            "file_id": str(result.file_id),
            "receipt_date": result.extracted.receipt_date,
            "store_name": result.extracted.store_name,
            "amount": result.extracted.amount,
            "payment_method": result.extracted.payment_method,
            "category": result.extracted.category,
            "confidence": result.extracted.confidence,
            "evidence_status": result.policy.evidence_status,
            "need_check": result.policy.need_check,
            "required_evidence": result.policy.required_evidence,
            "reason": result.policy.reason,
            "saved": result.saved,
            "model": result.model,
            "activity_report_id": str(linked_activity_id) if linked_activity_id else None,
        }

        activity_msg = ""
        if activity_res.mode == "linked" and activity_res.activity_title:
            activity_msg = f" ({activity_res.activity_title} 증빙으로 연결)"

        msg = (
            f"영수증 분석이 완료되었습니다{activity_msg}. "
            f"가맹점: {result.extracted.store_name or '알 수 없음'}, "
            f"금액: {result.extracted.amount:,}원, "
            f"증빙 상태: {result.policy.evidence_status}"
        )
        if not save:
            msg += " (DB 저장하려면 '확인 후 반영' 버튼을 클릭하세요)"

        detail_url = f"/activities/{activity_res.activity_id}" if activity_res.mode == "linked" and activity_res.activity_id else "/receipts"

        apply_payload = {
            "intent": "receipt_analysis",
            "file_id": str(file_id),
            "auto_apply": True,
            "activity_id": activity_res.activity_id,
        }

        return AssistantExecuteResponse(
            intent="receipt_analysis",
            confidence=ir.confidence,
            agent_flow=["IntentRouter", "FileParser", "ReceiptAgent", "ClassifierAgent", "PolicyAgent", "PublisherAgent"],
            result_type="receipt_analysis",
            result=result_dict,
            requires_confirmation=not save,
            message=msg,
            apply_payload=apply_payload if not save else None,
            detail_url=detail_url,
        )

    # ------------------------------------------------------------------
    # bank_statement_import
    # ------------------------------------------------------------------

    def _bank_statement(self, inp: AssistantInput, ir: IntentResult) -> AssistantExecuteResponse:
        if not inp.file_ids or not inp.file_paths:
            return AssistantExecuteResponse(
                intent="bank_statement_import",
                confidence=ir.confidence,
                agent_flow=["IntentRouter"],
                result_type="error",
                result={"error": "거래내역서 파일이 필요합니다."},
                requires_confirmation=False,
                message="Excel 또는 CSV 파일을 첨부해 주세요.",
                detail_url="/transactions",
            )

        from app.services.bank_statement_parser import parse_bank_statement
        from app.models import BankTransaction
        from sqlalchemy import select

        file_path = inp.file_paths[0]
        file_name = inp.file_names[0] if inp.file_names else "statement"

        parsed = parse_bank_statement(file_path)

        if inp.auto_apply:
            from app.routers.common import commit_or_400
            existing_keys: set[tuple] = set()
            existing_rows = self.db.execute(select(BankTransaction)).scalars().all()
            for row in existing_rows:
                existing_keys.add((
                    str(row.transaction_datetime),
                    row.memo,
                    row.withdraw_amount,
                    row.deposit_amount,
                    row.balance,
                ))

            inserted = 0
            duplicates = 0
            for tx in parsed.transactions:
                key = (
                    str(tx.transaction_datetime),
                    tx.memo,
                    tx.withdraw_amount,
                    tx.deposit_amount,
                    tx.balance,
                )
                if key in existing_keys:
                    duplicates += 1
                    continue
                record = BankTransaction(
                    transaction_datetime=tx.transaction_datetime,
                    transaction_type=tx.transaction_type,
                    memo=tx.memo,
                    withdraw_amount=tx.withdraw_amount,
                    deposit_amount=tx.deposit_amount,
                    balance=tx.balance,
                    branch=tx.branch,
                    match_status="unmatched",
                )
                self.db.add(record)
                existing_keys.add(key)
                inserted += 1

            self.db.commit()

            result_dict = {
                "file_name": file_name,
                "total_rows": parsed.total_rows,
                "parsed_rows": parsed.parsed_rows,
                "inserted_rows": inserted,
                "duplicate_rows": duplicates,
                "skipped_rows": parsed.skipped_rows,
                "errors": parsed.errors,
                "warnings": parsed.warnings,
            }
            return AssistantExecuteResponse(
                intent="bank_statement_import",
                confidence=ir.confidence,
                agent_flow=["IntentRouter", "BankStatementParser", "DBImport"],
                result_type="bank_statement_import_result",
                result=result_dict,
                requires_confirmation=False,
                message=f"거래내역서 가져오기 완료: {inserted}건 저장, {duplicates}건 중복 스킵",
                detail_url="/transactions",
            )
        else:
            preview_txs = [
                {
                    "transaction_datetime": str(tx.transaction_datetime) if tx.transaction_datetime else None,
                    "transaction_type": tx.transaction_type,
                    "memo": tx.memo,
                    "withdraw_amount": tx.withdraw_amount,
                    "deposit_amount": tx.deposit_amount,
                    "balance": tx.balance,
                    "branch": tx.branch,
                    "warnings": tx.warnings,
                }
                for tx in parsed.transactions[:20]
            ]
            result_dict = {
                "file_name": file_name,
                "total_rows": parsed.total_rows,
                "parsed_rows": parsed.parsed_rows,
                "skipped_rows": parsed.skipped_rows,
                "preview_transactions": preview_txs,
                "errors": parsed.errors,
                "warnings": parsed.warnings,
            }
            apply_payload = {
                "intent": "bank_statement_import",
                "auto_apply": True,
                "parsed_rows": parsed.parsed_rows,
            }
            return AssistantExecuteResponse(
                intent="bank_statement_import",
                confidence=ir.confidence,
                agent_flow=["IntentRouter", "BankStatementParser"],
                result_type="bank_statement_preview",
                result=result_dict,
                requires_confirmation=True,
                message=f"거래내역서 미리보기: {parsed.parsed_rows}건 파싱. 확인 후 반영 버튼을 클릭하면 DB에 저장됩니다.",
                apply_payload=apply_payload,
                detail_url="/transactions",
            )

    # ------------------------------------------------------------------
    # payment_matching
    # ------------------------------------------------------------------

    def _payment_matching(self, inp: AssistantInput, ir: IntentResult) -> AssistantExecuteResponse:
        from app.services.payment_matching_service import (
            preview_payment_matching,
            apply_payment_matching,
        )

        period = inp.period
        payment_type = inp.payment_type
        required_amount = inp.required_amount

        if inp.auto_apply:
            result = apply_payment_matching(
                db=self.db,
                period=period,
                payment_type=payment_type,
                required_amount=required_amount,
            )
            result_dict = {
                "period": result.period,
                "payment_type": result.payment_type,
                "required_amount": result.required_amount,
                "total_active_members": result.total_active_members,
                "matched_count": result.matched_count,
                "need_check_count": result.need_check_count,
                "unpaid_count": result.unpaid_count,
                "excluded_count": result.excluded_count,
                "created_payment_records": result.created_payment_records,
                "updated_payment_records": result.updated_payment_records,
                "updated_transactions": result.updated_transactions,
            }
            msg = (
                f"납부 매칭 적용 완료 ({period}, {payment_type}): "
                f"매칭 {result.matched_count}건, 미납 {result.unpaid_count}명"
            )
            return AssistantExecuteResponse(
                intent="payment_matching",
                confidence=ir.confidence,
                agent_flow=["IntentRouter", "PaymentMatchingService", "DBApply"],
                result_type="payment_matching_result",
                result=result_dict,
                requires_confirmation=False,
                message=msg,
                detail_url="/payments",
            )
        else:
            preview = preview_payment_matching(
                db=self.db,
                period=period,
                payment_type=payment_type,
                required_amount=required_amount,
            )
            unpaid_names = [m.name for m in preview.unpaid_members[:5]]
            result_dict = {
                "period": preview.period,
                "payment_type": preview.payment_type,
                "required_amount": preview.required_amount,
                "total_active_members": preview.total_active_members,
                "matched_count": preview.matched_count,
                "need_check_count": preview.need_check_count,
                "unpaid_count": preview.unpaid_count,
                "excluded_count": preview.excluded_count,
                "unpaid_sample": unpaid_names,
            }
            apply_payload = {
                "period": period,
                "payment_type": payment_type,
                "required_amount": required_amount,
            }
            msg = (
                f"납부 매칭 미리보기 ({period}, {payment_type}): "
                f"매칭 {preview.matched_count}건, 확인 필요 {preview.need_check_count}건, "
                f"미납 {preview.unpaid_count}명. 확인 후 반영 버튼으로 적용할 수 있습니다."
            )
            return AssistantExecuteResponse(
                intent="payment_matching",
                confidence=ir.confidence,
                agent_flow=["IntentRouter", "PaymentMatchingService"],
                result_type="payment_matching_preview",
                result=result_dict,
                requires_confirmation=True,
                message=msg,
                apply_payload=apply_payload,
                detail_url="/payments",
            )

    # ------------------------------------------------------------------
    # activity_report_generate
    # ------------------------------------------------------------------

    def _activity_report(
        self,
        inp: AssistantInput,
        ir: IntentResult,
        activity_res: ActivityResolutionResult,
    ) -> AssistantExecuteResponse:
        from sqlalchemy import select
        from app.models.activity import ActivityCategory, ActivityReport, ActivityParticipant
        from app.agents.activity_report_orchestrator import ActivityReportOrchestrator, OrchestratorInput

        # Use linked activity's category if available
        category_id = None
        category_name = None
        report_template = None
        linked_report_id: UUID | None = None

        if activity_res.mode == "linked" and activity_res.activity_id:
            try:
                linked_activity_uuid = UUID(activity_res.activity_id)
                linked_report = self.db.get(ActivityReport, linked_activity_uuid)
                if linked_report and linked_report.category_id:
                    cat = self.db.get(ActivityCategory, linked_report.category_id)
                    if cat:
                        category_id = cat.id
                        category_name = cat.name
                        report_template = cat.report_template
                linked_report_id = linked_activity_uuid
            except (ValueError, AttributeError):
                pass

        if category_id is None:
            first_cat = self.db.execute(select(ActivityCategory).limit(1)).scalar_one_or_none()
            if first_cat is None:
                return AssistantExecuteResponse(
                    intent="activity_report_generate",
                    confidence=ir.confidence,
                    agent_flow=["IntentRouter"],
                    result_type="error",
                    result={"error": "활동 카테고리가 없습니다. 설정에서 카테고리를 먼저 등록하세요."},
                    requires_confirmation=False,
                    message="활동 카테고리가 없습니다.",
                    detail_url="/settings",
                )
            category_id = first_cat.id
            category_name = first_cat.name
            report_template = first_cat.report_template

        title = inp.message or "새 활동 보고서"
        if activity_res.mode == "linked" and activity_res.activity_title:
            title = activity_res.activity_title

        if len(title) > 100:
            title = title[:100]

        orch_input = OrchestratorInput(
            category_id=category_id,
            category_name=category_name,
            report_template=report_template,
            title=title,
            input_text=inp.message,
            file_ids=inp.file_ids,
            save_to_db=inp.auto_apply,
            activity_report_id=linked_report_id,
        )
        output = ActivityReportOrchestrator(self.db).run(orch_input)

        result_dict = {
            "title": output.title,
            "summary": output.summary,
            "content": output.content,
            "missing_fields": output.missing_fields,
            "confidence": output.confidence,
            "model": output.model,
            "saved": output.saved,
            "activity_report_id": str(output.activity_report_id) if output.activity_report_id else None,
        }

        activity_msg = ""
        if activity_res.mode == "linked" and activity_res.activity_title:
            activity_msg = f" ({activity_res.activity_title} 활동에 연결)"

        msg = f"활동 보고서 초안이 생성되었습니다: '{output.title}'{activity_msg}"
        if not inp.auto_apply:
            msg += " (확인 후 반영 버튼을 클릭하면 저장됩니다)"

        detail_url = f"/activities/{activity_res.activity_id}" if activity_res.mode == "linked" and activity_res.activity_id else "/reports"

        return AssistantExecuteResponse(
            intent="activity_report_generate",
            confidence=ir.confidence,
            agent_flow=["IntentRouter", "FileParser", "PostAgent", "PublisherAgent"],
            result_type="activity_report_draft",
            result=result_dict,
            requires_confirmation=not inp.auto_apply,
            message=msg,
            apply_payload=None,
            detail_url=detail_url,
        )

    # ------------------------------------------------------------------
    # activity_fee_generate (Task 17)
    # ------------------------------------------------------------------

    def _activity_fee_generate(
        self,
        inp: AssistantInput,
        ir: IntentResult,
        activity_res: ActivityResolutionResult,
    ) -> AssistantExecuteResponse:
        from sqlalchemy import and_, select
        from app.models.activity import ActivityParticipant
        from app.models.payment import PaymentRecord

        # Need a linked activity
        if activity_res.mode != "linked" or not activity_res.activity_id:
            return AssistantExecuteResponse(
                intent="activity_fee_generate",
                confidence=ir.confidence,
                agent_flow=["Activity Resolver", "Budget Agent"],
                result_type="general_message",
                result={},
                requires_confirmation=True,
                message="활동비를 생성하려면 먼저 활동을 선택하거나 활동 상세 페이지에서 실행해 주세요.",
                activity_context=_build_activity_context_dict(activity_res),
                activity_candidates=_build_candidates_list(activity_res),
                detail_url="/activities",
            )

        try:
            activity_uuid = UUID(activity_res.activity_id)
        except (ValueError, AttributeError):
            return AssistantExecuteResponse(
                intent="activity_fee_generate",
                confidence=ir.confidence,
                agent_flow=["Activity Resolver", "Budget Agent"],
                result_type="error",
                result={"error": "Invalid activity_id"},
                requires_confirmation=False,
                message="활동 ID가 올바르지 않습니다.",
                detail_url="/activities",
            )

        # Extract fee amount from message
        fee_amount = _extract_amount(inp.message or "")
        if fee_amount is None:
            return AssistantExecuteResponse(
                intent="activity_fee_generate",
                confidence=ir.confidence,
                agent_flow=["Activity Resolver", "Budget Agent"],
                result_type="general_message",
                result={"activity_id": activity_res.activity_id},
                requires_confirmation=True,
                message=f"활동비 금액을 입력해 주세요. 예: '참여자 기준 활동비 10000원 납부 대상 만들어줘'",
                activity_context=_build_activity_context_dict(activity_res),
                detail_url=f"/activities/{activity_res.activity_id}",
            )

        # Get participants
        participants = list(self.db.scalars(
            select(ActivityParticipant).where(ActivityParticipant.activity_report_id == activity_uuid)
        ))
        if not participants:
            return AssistantExecuteResponse(
                intent="activity_fee_generate",
                confidence=ir.confidence,
                agent_flow=["Activity Resolver", "Budget Agent"],
                result_type="general_message",
                result={},
                requires_confirmation=False,
                message="참여자가 없습니다. 먼저 활동 상세 페이지에서 참여자를 추가하세요.",
                activity_context=_build_activity_context_dict(activity_res),
                detail_url=f"/activities/{activity_res.activity_id}",
            )

        period_key = f"act-{activity_res.activity_id[:8]}"
        created = 0
        skipped = 0
        for p in participants:
            existing = self.db.execute(
                select(PaymentRecord).where(
                    and_(
                        PaymentRecord.member_id == p.member_id,
                        PaymentRecord.period == period_key,
                        PaymentRecord.payment_type == "activity_fee",
                    )
                )
            ).scalar_one_or_none()

            if existing:
                if existing.status not in ("paid", "partial", "exempt"):
                    existing.required_amount = fee_amount
                skipped += 1
            else:
                record = PaymentRecord(
                    member_id=p.member_id,
                    period=period_key,
                    payment_type="activity_fee",
                    required_amount=fee_amount,
                    paid_amount=0,
                    status="unpaid",
                    activity_report_id=activity_uuid,
                )
                self.db.add(record)
                created += 1

        self.db.commit()

        result_dict = {
            "activity_id": activity_res.activity_id,
            "activity_title": activity_res.activity_title,
            "fee_amount": fee_amount,
            "period_key": period_key,
            "created_count": created,
            "updated_count": skipped,
            "total_participants": len(participants),
        }

        return AssistantExecuteResponse(
            intent="activity_fee_generate",
            confidence=ir.confidence,
            agent_flow=["Activity Resolver", "Budget Agent", "Publisher Agent"],
            result_type="activity_fee_generation_result",
            result=result_dict,
            requires_confirmation=False,
            message=f"참여자 {len(participants)}명 기준으로 활동비 {fee_amount:,}원 납부 대상을 생성했습니다. (신규 {created}건)",
            activity_context=_build_activity_context_dict(activity_res),
            detail_url=f"/activities/{activity_res.activity_id}",
        )

    # ------------------------------------------------------------------
    # activity_link (Task 17)
    # ------------------------------------------------------------------

    def _activity_link(
        self,
        inp: AssistantInput,
        ir: IntentResult,
        activity_res: ActivityResolutionResult,
    ) -> AssistantExecuteResponse:
        if activity_res.mode == "linked" and inp.file_ids:
            # Treat as receipt analysis linked to activity
            return self._receipt_analysis(inp, ir, activity_res)

        return AssistantExecuteResponse(
            intent="activity_link",
            confidence=ir.confidence,
            agent_flow=["Activity Resolver"],
            result_type="general_message",
            result={},
            requires_confirmation=activity_res.mode in ("needs_confirmation", "candidate"),
            message="연결할 활동과 파일을 함께 제출해 주세요.",
            activity_context=_build_activity_context_dict(activity_res),
            activity_candidates=_build_candidates_list(activity_res),
            detail_url="/activities",
        )

    # ------------------------------------------------------------------
    # activity_create (Task 17)
    # ------------------------------------------------------------------

    def _activity_create_prompt(
        self,
        inp: AssistantInput,
        ir: IntentResult,
        activity_res: ActivityResolutionResult,
    ) -> AssistantExecuteResponse:
        from app.agents.activity_resolver import _build_draft
        draft = _build_draft(inp.message or "") or {
            "title": inp.message[:60] if inp.message else "새 활동",
            "activity_date": None,
            "location": None,
            "description": inp.message,
        }
        return AssistantExecuteResponse(
            intent="activity_create",
            confidence=ir.confidence,
            agent_flow=["Activity Resolver"],
            result_type="activity_draft",
            result={},
            requires_confirmation=True,
            message="새 활동을 생성할까요?",
            activity_context={"mode": "create_draft", "confidence": 0.9},
            activity_draft=draft,
            detail_url="/activities",
        )

    # ------------------------------------------------------------------
    # _unknown
    # ------------------------------------------------------------------

    def _unknown(self, inp: AssistantInput, ir: IntentResult) -> AssistantExecuteResponse:
        return AssistantExecuteResponse(
            intent="unknown",
            confidence=0.0,
            agent_flow=["IntentRouter"],
            result_type="general_message",
            result={},
            requires_confirmation=False,
            message=(
                "요청을 정확히 분류하지 못했습니다. "
                "영수증 분석, 거래내역서 분석, 납부 매칭, 활동 보고서 생성 중 "
                "하나를 선택해 다시 실행해 주세요."
            ),
            detail_url="/assistant",
        )


def _extract_amount(message: str) -> int | None:
    """Extract a monetary amount (KRW) from a message string."""
    patterns = [
        r'(\d{1,3}(?:,\d{3})*)\s*원',
        r'(\d+)\s*원',
        r'(\d{4,})',
    ]
    for pat in patterns:
        m = re.search(pat, message.replace(",", ""))
        if m:
            try:
                amount = int(m.group(1).replace(",", ""))
                if amount >= 100:
                    return amount
            except ValueError:
                pass
    return None
