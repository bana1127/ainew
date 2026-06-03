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
from datetime import date, timedelta
from pathlib import Path
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.agents.activity_resolver import ActivityResolutionResult, resolve_activity_context
from app.agents.intent_router import (
    PARTICIPANT_IMPORT_KEYWORDS,
    ROSTER_KEYWORDS,
    IntentResult,
    route,
)
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
    "payment_manual_update_result": "/payments?tab=activity_fee",
    "activity_import_result": "/activities",
    "general_message": "/dashboard",
    "error": "/assistant",
}

MEMBERSHIP_FEE_KEYWORDS = ("회비", "학기 회비", "부원 회비")
ACTIVITY_FEE_KEYWORDS = ("활동비", "참가비", "체험비", "해당 활동 비용", "활동 비용")

ACTIVITY_CREATE_FILE_INTENTS = {
    "activity_create_with_roster",
    "activity_create_with_application_form",
    "activity_create_with_file",
}


def _infer_payment_type_from_text(message: str | None) -> str | None:
    text = message or ""
    has_membership_fee = any(keyword in text for keyword in MEMBERSHIP_FEE_KEYWORDS)
    has_activity_fee = any(keyword in text for keyword in ACTIVITY_FEE_KEYWORDS)
    if has_membership_fee and not has_activity_fee:
        return "membership_fee"
    if has_activity_fee and not has_membership_fee:
        return "activity_fee"
    return None


def _payment_type_label(payment_type: str | None) -> str:
    if payment_type == "membership_fee":
        return "회비"
    if payment_type == "activity_fee":
        return "활동비"
    return "납부"


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
    required_amount: int = 0  # 0 = use each record's own amount (no legacy default)
    # Task 17: Activity context
    activity_id: UUID | None = None
    activity_mode: str = "auto"
    create_activity_if_missing: bool = False


@dataclass
class ActivityFieldInference:
    title: str
    activity_date: date | None = None
    location: str | None = None
    description: str | None = None


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


def _intent_for_create_new_files(inp: AssistantInput, fallback: IntentResult) -> IntentResult:
    message = (inp.message or "").lower()
    joined_names = " ".join(inp.file_names).lower()
    text = f"{message} {joined_names}"
    if any(word in text for word in ("명단", "명부", "roster", "부원")):
        return IntentResult("activity_create_with_roster", 0.98, "activity_mode=create_new with roster file")
    if any(word in text for word in ("신청", "모집", "application", "apply", "응답")):
        return IntentResult("activity_create_with_application_form", 0.98, "activity_mode=create_new with application form")
    return IntentResult("activity_create_with_file", max(fallback.confidence, 0.95), "activity_mode=create_new with uploaded file")


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

        pre_intent_result: IntentResult = route(
            message=inp.message,
            file_names=inp.file_names,
            requested_intent=inp.requested_intent,
        )
        if inp.activity_mode == "create_new" and inp.file_names:
            pre_intent_result = _intent_for_create_new_files(inp, pre_intent_result)
        elif inp.activity_id and inp.file_names and pre_intent_result.intent in ACTIVITY_CREATE_FILE_INTENTS:
            message = (inp.message or "").strip()
            if any(kw in message for kw in PARTICIPANT_IMPORT_KEYWORDS | ROSTER_KEYWORDS):
                pre_intent_result = IntentResult(
                    "participant_import",
                    max(pre_intent_result.confidence, 0.93),
                    "Existing activity context + spreadsheet participant keywords",
                )
        pre_intent = pre_intent_result.intent

        # If resolver needs user confirmation, return early unless this is a
        # file-driven new activity flow. That flow intentionally creates the
        # activity first and then links/imports the uploaded file.
        if (
            activity_res.mode in ("needs_confirmation", "create_draft")
            and inp.activity_id is None
            and pre_intent not in ACTIVITY_CREATE_FILE_INTENTS
        ):
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
        intent_result = pre_intent_result
        intent = intent_result.intent

        # ── Step 3: Execute based on intent + activity context ─────────────
        activity_context = _build_activity_context_dict(activity_res)
        candidates = _build_candidates_list(activity_res)

        # Add "Activity Resolver" to agent flow prefix
        def with_resolver(flow: list[str]) -> list[str]:
            return ["Activity Resolver"] + flow if activity_res.mode != "none" else flow

        try:
            if intent == "payment_manual_update":
                resp = self._payment_manual_update(inp, intent_result, activity_res)
            elif intent == "activity_fee_generate":
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
            elif intent in ACTIVITY_CREATE_FILE_INTENTS:
                resp = self._activity_create_with_files(inp, intent_result)
            elif intent == "activity_create":
                resp = self._activity_create_prompt(inp, intent_result, activity_res)
            elif intent == "participant_import":
                resp = self._participant_import(inp, intent_result, activity_res)
            elif intent == "bulk_membership_fee_mark_paid":
                resp = self._bulk_membership_fee_mark_paid(inp, intent_result)
            elif intent == "membership_fee_generate":
                resp = self._membership_fee_generate(inp, intent_result)
            elif intent == "activity_fee_transaction_match":
                resp = self._activity_fee_transaction_match(inp, intent_result, activity_res)
            else:
                resp = self._unknown(inp, intent_result)

            # Attach activity context to all responses
            if activity_res.mode != "none":
                if resp.activity_context is None:
                    resp.activity_context = activity_context
                if candidates and not resp.activity_candidates:
                    resp.activity_candidates = candidates
                if activity_res.draft and resp.activity_draft is None:
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
        from app.services.assistant_action_service import create_action_proposal

        file_id = inp.file_ids[0]
        file_path = inp.file_paths[0] if inp.file_paths else None
        file_name = inp.file_names[0] if inp.file_names else "receipt"
        mime_type = inp.mime_types[0] if inp.mime_types else None

        # Task 25: always analyse without saving — proposal required for actual save
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
            save_to_db=False,
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
            "saved": False,
            "model": result.model,
            "activity_report_id": str(linked_activity_id) if linked_activity_id else None,
        }

        # Save proposal so confirm endpoint can apply
        proposal = create_action_proposal(
            self.db,
            action_type="receipt_analysis",
            source="activity_detail" if inp.activity_id else "assistant",
            activity_id=linked_activity_id,
            payload={
                "file_id": str(file_id),
                "activity_report_id": str(linked_activity_id) if linked_activity_id else None,
                "extracted": {
                    "receipt_date": result.extracted.receipt_date,
                    "store_name": result.extracted.store_name,
                    "amount": result.extracted.amount,
                    "payment_method": result.extracted.payment_method,
                    "category": result.extracted.category,
                    "raw_text": getattr(result.extracted, "raw_text", None),
                    "confidence": result.extracted.confidence,
                },
                "policy": {
                    "evidence_status": result.policy.evidence_status,
                    "need_check": result.policy.need_check,
                    "required_evidence": result.policy.required_evidence,
                    "reason": result.policy.reason,
                },
            },
            preview={
                "store_name": result.extracted.store_name,
                "amount": result.extracted.amount,
                "evidence_status": result.policy.evidence_status,
                "activity_title": activity_res.activity_title,
            },
            confidence=ir.confidence,
            risk_level="low",
        )
        result_dict["action_id"] = str(proposal.id)
        result_dict["proposal_status"] = proposal.status

        activity_msg = ""
        if activity_res.mode == "linked" and activity_res.activity_title:
            activity_msg = f" ({activity_res.activity_title} 증빙으로 연결)"

        msg = (
            f"영수증 분석이 완료되었습니다{activity_msg}. "
            f"가맹점: {result.extracted.store_name or '알 수 없음'}, "
            f"금액: {result.extracted.amount:,}원. "
            f"확인 후 반영을 눌러야 저장됩니다."
        )

        detail_url = f"/activities/{activity_res.activity_id}" if activity_res.mode == "linked" and activity_res.activity_id else "/receipts"

        return AssistantExecuteResponse(
            intent="receipt_analysis",
            confidence=ir.confidence,
            agent_flow=["IntentRouter", "FileParser", "ReceiptAgent", "ClassifierAgent", "PolicyAgent", "PublisherAgent"],
            result_type="receipt_analysis",
            result=result_dict,
            requires_confirmation=True,
            message=msg,
            apply_payload={"action_id": str(proposal.id)},
            detail_url=detail_url,
        )

    # ------------------------------------------------------------------
    # google_form_import  (Task 18)
    # ------------------------------------------------------------------

    def _activity_create_with_files(
        self,
        inp: AssistantInput,
        ir: IntentResult,
    ) -> AssistantExecuteResponse:
        """Create a new activity, attach uploaded files, and apply roster/form imports when safe."""
        logger.warning("[assistant] intent=%s", ir.intent)
        logger.warning("[assistant] uploaded_files_count=%s", len(inp.file_ids))
        logger.warning("[assistant] activity_action=create")
        if not inp.file_ids:
            return AssistantExecuteResponse(
                intent=ir.intent,
                confidence=ir.confidence,
                agent_flow=["IntentRouter"],
                result_type="error",
                result={"error": "No uploaded file"},
                requires_confirmation=False,
                message="활동을 만들 파일을 첨부해 주세요.",
                detail_url="/assistant",
            )

        from app.models.activity import ActivityReport
        from app.models.file import UploadedFile
        from app.services.google_form_import_service import apply_import, preview_import

        fields = _infer_activity_fields(inp.message or "", inp.file_names)
        activity_fee_amount = _extract_activity_fee_amount(inp.message or "")
        logger.warning("[assistant] activity_mode=%s", inp.activity_mode)
        logger.warning("[assistant] extracted_title=%s", fields.title)
        logger.warning("[assistant] extracted_date=%s", fields.activity_date)
        logger.warning("[assistant] extracted_location=%s", fields.location)
        logger.warning("[assistant] activity_fee_amount=%s", activity_fee_amount)
        report = ActivityReport(
            title=fields.title,
            activity_date=fields.activity_date,
            location=fields.location,
            input_text=inp.message,
            status="planned",
        )
        self.db.add(report)
        self.db.flush()
        logger.warning("[assistant] created_activity_id=%s", report.id)

        linked_files: list[dict] = []
        spreadsheet: tuple[Path, str] | None = None
        for file_id, file_name, file_path, mime_type in zip(
            inp.file_ids,
            inp.file_names,
            inp.file_paths,
            inp.mime_types,
        ):
            record = self.db.get(UploadedFile, file_id)
            if not record:
                continue
            record.activity_report_id = report.id
            record.related_entity_type = "activity_report"
            record.related_entity_id = report.id
            if not record.stored_filename:
                record.stored_filename = file_path.name
            if not record.file_ext:
                record.file_ext = file_path.suffix.lower().lstrip(".") or None
            if record.size_bytes is None and file_path.exists():
                record.size_bytes = file_path.stat().st_size

            linked_files.append(
                {
                    "file_id": str(record.id),
                    "original_filename": record.original_filename,
                    "file_category": record.file_category,
                    "file_role": record.file_role,
                }
            )
            if file_path.suffix.lower() in (".xlsx", ".xls", ".csv") and spreadsheet is None:
                spreadsheet = (file_path, file_name)
        logger.warning("[assistant] linked_file_ids=%s", [str(fid) for fid in inp.file_ids])
        logger.warning("[assistant] has_spreadsheet=%s", spreadsheet is not None)

        import_result = None
        preview_result = None
        activity_fee_result = None
        risk_reasons: list[str] = []
        requires_confirmation = False

        if spreadsheet:
            file_path, file_name = spreadsheet
            form_stage = "auto"
            if ir.intent == "activity_create_with_roster":
                form_stage = "roster"
            elif ir.intent == "activity_create_with_application_form":
                form_stage = "before"
            preview = preview_import(
                db=self.db,
                file_bytes=file_path.read_bytes(),
                filename=file_name,
                activity_id=str(report.id),
                form_stage=form_stage,
            )
            preview_result = preview
            logger.warning("[assistant] excel_form_type=%s", preview.form_type)
            logger.warning("[assistant] import_preview_total_rows=%s", preview.summary.total_rows)

            for file_id in inp.file_ids:
                record = self.db.get(UploadedFile, file_id)
                if record and record.original_filename == file_name:
                    _apply_form_file_category(record, preview.form_type)
                    break

            risk_reasons = _import_risk_reasons(preview)
            # Task 25: always require confirmation for import — never auto-apply
            requires_confirmation = True
        else:
            self.db.commit()

        self.db.commit()

        self.db.refresh(report)

        saved_file_rows = list(
            self.db.scalars(
                select(UploadedFile).where(UploadedFile.activity_report_id == report.id)
            )
        )
        linked_files = [
            {
                "file_id": str(record.id),
                "original_filename": record.original_filename,
                "file_category": record.file_category,
                "file_role": record.file_role,
                "stored_filename": record.stored_filename,
                "file_ext": record.file_ext,
                "size_bytes": record.size_bytes,
            }
            for record in saved_file_rows
        ]

        import_summary = None
        if import_result:
            import_summary = {
                "form_type": import_result.form_type,
                "total_rows": preview_result.summary.total_rows if preview_result else 0,
                "created_members": import_result.created_members,
                "updated_members": import_result.updated_members,
                "created_participants": import_result.created_participants,
                "updated_participants": import_result.updated_participants,
                "saved_feedbacks": import_result.saved_feedbacks,
                "needs_review": preview_result.summary.needs_review if preview_result else 0,
            }
        elif preview_result:
            import_summary = {
                "form_type": preview_result.form_type,
                "total_rows": preview_result.summary.total_rows,
                "matched_members": preview_result.summary.matched_members,
                "new_member_candidates": preview_result.summary.new_member_candidates,
                "needs_review": preview_result.summary.needs_review,
                "existing_participants": preview_result.summary.existing_participants,
                "new_participants": preview_result.summary.new_participants,
            }

        result_dict = {
            "activity": {
                "id": str(report.id),
                "title": report.title,
                "activity_date": str(report.activity_date) if report.activity_date else None,
                "location": report.location,
                "detail_url": f"/activities/{report.id}",
            },
            "files": linked_files,
            "file_results": linked_files,
            "form_type": preview_result.form_type if preview_result else None,
            "import_summary": import_summary,
            "import_result": import_summary,
            "activity_fee_result": activity_fee_result,
            "risk_reasons": risk_reasons,
        }

        # Task 25: always create proposal for import — never auto-apply
        apply_payload = None
        if preview_result and preview_result.form_type in ("activity_application_form", "activity_feedback_form", "member_roster"):
            from app.services.assistant_action_service import create_action_proposal
            import_proposal = create_action_proposal(
                self.db,
                action_type="google_form_import",
                source="assistant",
                activity_id=report.id,
                payload={
                    "activity_id": str(report.id),
                    "form_type": preview_result.form_type,
                    "rows": [_import_row_to_dict(r) for r in preview_result.rows],
                    "activity_fee_amount": activity_fee_amount,
                },
                preview={
                    "form_type": preview_result.form_type,
                    "total_rows": preview_result.summary.total_rows,
                    "matched_members": preview_result.summary.matched_members,
                    "new_member_candidates": preview_result.summary.new_member_candidates,
                    "activity_title": report.title,
                },
                confidence=ir.confidence,
                risk_level="medium",
            )
            apply_payload = {"action_id": str(import_proposal.id)}

        if requires_confirmation and preview_result:
            msg = (
                f"'{report.title}' 활동 생성 및 파일 연결이 완료됐습니다. "
                f"명단 {preview_result.summary.total_rows}명 반영은 확인 후 반영을 눌러야 적용됩니다."
            )
        else:
            msg = f"'{report.title}' 활동을 만들고 파일 {len(linked_files)}개를 연결했습니다."

        return AssistantExecuteResponse(
            intent=ir.intent,
            confidence=ir.confidence,
            agent_flow=["IntentRouter", "ActivityCreate", "FileVault", "GoogleFormImportService"],
            result_type="activity_import_result",
            result=result_dict,
            requires_confirmation=requires_confirmation,
            message=msg,
            apply_payload=apply_payload,
            detail_url=f"/activities/{report.id}",
            activity_context={
                "mode": "created",
                "confidence": ir.confidence,
                "activity_id": str(report.id),
                "activity_title": report.title,
                "activity_date": str(report.activity_date) if report.activity_date else None,
                "location": report.location,
                "detail_url": f"/activities/{report.id}",
            },
        )

    def _google_form_import(
        self,
        inp: AssistantInput,
        ir: IntentResult,
        file_bytes: bytes,
        file_name: str,
        classification,
    ) -> AssistantExecuteResponse:
        """Handle activity application / feedback form Excel files."""
        from app.services.google_form_import_service import preview_import
        from app.agents.activity_resolver import ActivityResolutionResult

        activity_id: str | None = str(inp.activity_id) if inp.activity_id else None

        try:
            preview = preview_import(
                db=self.db,
                file_bytes=file_bytes,
                filename=file_name,
                activity_id=activity_id,
                form_stage="auto",
            )
        except Exception as exc:
            return AssistantExecuteResponse(
                intent="bank_statement_import",
                confidence=ir.confidence,
                agent_flow=["IntentRouter", "ExcelFormClassifier"],
                result_type="error",
                result={"error": str(exc)},
                requires_confirmation=False,
                message=f"Google Form 파일 처리 중 오류: {exc}",
                detail_url="/assistant",
            )

        form_type_label = {
            "activity_application_form": "활동 신청서",
            "activity_feedback_form": "활동 후 피드백/활동지",
            "member_roster": "부원 명단",
        }.get(preview.form_type, preview.form_type)

        if inp.auto_apply and preview.activity_context.activity_id:
            risks = _import_risk_reasons(preview)
            if not risks and preview.form_type in ("activity_application_form", "activity_feedback_form", "member_roster"):
                from app.services.google_form_import_service import apply_import
                applied = apply_import(
                    db=self.db,
                    activity_id=preview.activity_context.activity_id,
                    form_type=preview.form_type,
                    rows=preview.rows,
                )
                return AssistantExecuteResponse(
                    intent="google_form_import",
                    confidence=classification.confidence,
                    agent_flow=["IntentRouter", "ExcelFormClassifier", "GoogleFormImportService", "DBApply"],
                    result_type="activity_import_result",
                    result={
                        "activity": {
                            "id": applied.activity_id,
                            "title": preview.activity_context.activity_title,
                        },
                        "form_type": applied.form_type,
                        "import_summary": {
                            "created_members": applied.created_members,
                            "updated_members": applied.updated_members,
                            "created_participants": applied.created_participants,
                            "updated_participants": applied.updated_participants,
                            "saved_feedbacks": applied.saved_feedbacks,
                        },
                    },
                    requires_confirmation=False,
                    message=(
                        f"{form_type_label} 반영이 완료되었습니다. "
                        f"참여자 {applied.created_participants + applied.updated_participants}명을 반영했습니다."
                    ),
                    detail_url=f"/activities/{applied.activity_id}",
                )

        result_dict = {
            "form_type": preview.form_type,
            "form_type_label": form_type_label,
            "confidence": preview.confidence,
            "matched_columns": preview.matched_columns,
            "activity_context": {
                "mode": preview.activity_context.mode,
                "activity_id": preview.activity_context.activity_id,
                "activity_title": preview.activity_context.activity_title,
            },
            "summary": {
                "total_rows": preview.summary.total_rows,
                "matched_members": preview.summary.matched_members,
                "new_member_candidates": preview.summary.new_member_candidates,
                "needs_review": preview.summary.needs_review,
                "existing_participants": preview.summary.existing_participants,
                "new_participants": preview.summary.new_participants,
            },
            "rows": [
                {
                    "row_index": r.row_index,
                    "name": r.name,
                    "student_id": r.student_id,
                    "phone": r.phone,
                    "member_match_status": r.member_match_status,
                    "participant_action": r.participant_action,
                    "participant_status": r.participant_status,
                }
                for r in preview.rows[:30]
            ],
            "import_id": preview.import_id,
        }

        activity_msg = ""
        if preview.activity_context.activity_title:
            activity_msg = f" (활동: {preview.activity_context.activity_title})"

        msg = (
            f"{form_type_label} 파일이 감지되었습니다{activity_msg}. "
            f"총 {preview.summary.total_rows}명, "
            f"기존 부원 {preview.summary.matched_members}명, "
            f"신규 후보 {preview.summary.new_member_candidates}명. "
            f"활동에 적용하시겠습니까?"
        )

        apply_payload = {
            "intent": "google_form_import",
            "import_id": preview.import_id,
            "form_type": preview.form_type,
            "activity_id": preview.activity_context.activity_id,
            "rows": [
                {
                    "row_index": r.row_index,
                    "name": r.name,
                    "student_id": r.student_id,
                    "phone": r.phone,
                    "email": r.email,
                    "department": r.department,
                    "submitted_at": r.submitted_at,
                    "member_match_status": r.member_match_status,
                    "member_id": r.member_id,
                    "participant_action": r.participant_action,
                    "participant_status": r.participant_status,
                    "raw_response": r.raw_response,
                }
                for r in preview.rows
            ],
        }

        detail_url = (
            f"/activities/{preview.activity_context.activity_id}"
            if preview.activity_context.activity_id
            else "/activities"
        )

        return AssistantExecuteResponse(
            intent="google_form_import",
            confidence=classification.confidence,
            agent_flow=["IntentRouter", "ExcelFormClassifier", "GoogleFormImportService"],
            result_type="google_form_import_preview",
            result=result_dict,
            requires_confirmation=True,
            message=msg,
            apply_payload=apply_payload,
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

        # ── Google Form form type detection ───────────────────────────────
        # Read header row to classify the file before attempting bank parse
        try:
            import pandas as pd
            from pathlib import Path as _Path
            _suffix = _Path(file_name).suffix.lower()
            _buf = file_path.read_bytes() if hasattr(file_path, "read_bytes") else open(file_path, "rb").read()
            import io as _io
            if _suffix in (".xlsx", ".xls"):
                _df_head = pd.read_excel(_io.BytesIO(_buf), nrows=1, dtype=str)
            else:
                _df_head = pd.read_csv(_io.BytesIO(_buf), nrows=1, dtype=str)
            _headers = [str(c) for c in _df_head.columns.tolist()]
            from app.services.excel_form_classifier import classify_excel_form
            _cls = classify_excel_form(_headers, file_name)
            if _cls.form_type in ("activity_application_form", "activity_feedback_form", "member_roster"):
                return self._google_form_import(inp, ir, _buf, file_name, _cls)
        except Exception as _exc:
            logger.debug("Form classification failed, falling back to bank parser: %s", _exc)

        parsed = parse_bank_statement(file_path)

        # Task 25: always preview — create proposal so confirm endpoint applies
        from app.services.assistant_action_service import create_action_proposal

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

        file_id_str = str(inp.file_ids[0]) if inp.file_ids else None
        proposal = create_action_proposal(
            self.db,
            action_type="bank_statement_import",
            source="assistant",
            activity_id=None,
            payload={
                "file_id": file_id_str,
                "file_name": file_name,
                "parsed_rows": parsed.parsed_rows,
            },
            preview={
                "file_name": file_name,
                "total_rows": parsed.total_rows,
                "parsed_rows": parsed.parsed_rows,
                "skipped_rows": parsed.skipped_rows,
            },
            confidence=ir.confidence,
            risk_level="low",
        )

        result_dict = {
            "file_name": file_name,
            "total_rows": parsed.total_rows,
            "parsed_rows": parsed.parsed_rows,
            "skipped_rows": parsed.skipped_rows,
            "preview_transactions": preview_txs,
            "errors": parsed.errors,
            "warnings": parsed.warnings,
            "action_id": str(proposal.id),
            "proposal_status": proposal.status,
        }
        return AssistantExecuteResponse(
            intent="bank_statement_import",
            confidence=ir.confidence,
            agent_flow=["IntentRouter", "BankStatementParser"],
            result_type="bank_statement_preview",
            result=result_dict,
            requires_confirmation=True,
            message=f"거래내역서 미리보기: {parsed.parsed_rows}건 파싱. 확인 후 반영을 눌러야 DB에 저장됩니다.",
            apply_payload={"action_id": str(proposal.id)},
            detail_url="/transactions",
        )

    # ------------------------------------------------------------------
    # payment_matching
    # ------------------------------------------------------------------

    def _payment_matching(self, inp: AssistantInput, ir: IntentResult) -> AssistantExecuteResponse:
        from app.services.payment_matching_service import preview_payment_matching
        from app.services.assistant_action_service import create_action_proposal

        period = inp.period
        payment_type = inp.payment_type
        required_amount = inp.required_amount

        # Task 25: always preview — create proposal for deferred apply
        preview = preview_payment_matching(
            db=self.db,
            period=period,
            payment_type=payment_type,
            required_amount=required_amount,
        )
        unpaid_names = [m.name for m in preview.unpaid_members[:5]]

        proposal = create_action_proposal(
            self.db,
            action_type="payment_matching",
            source="assistant",
            activity_id=None,
            payload={
                "period": period,
                "payment_type": payment_type,
                "required_amount": required_amount,
            },
            preview={
                "period": preview.period,
                "payment_type": preview.payment_type,
                "matched_count": preview.matched_count,
                "need_check_count": preview.need_check_count,
                "unpaid_count": preview.unpaid_count,
            },
            confidence=ir.confidence,
            risk_level="medium",
        )

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
            "action_id": str(proposal.id),
            "proposal_status": proposal.status,
        }
        msg = (
            f"납부 매칭 미리보기 ({period}, {payment_type}): "
            f"매칭 {preview.matched_count}건, 확인 필요 {preview.need_check_count}건, "
            f"미납 {preview.unpaid_count}명. 확인 후 반영을 눌러야 적용됩니다."
        )
        return AssistantExecuteResponse(
            intent="payment_matching",
            confidence=ir.confidence,
            agent_flow=["IntentRouter", "PaymentMatchingService"],
            result_type="payment_matching_preview",
            result=result_dict,
            requires_confirmation=True,
            message=msg,
            apply_payload={"action_id": str(proposal.id)},
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
            save_to_db=False,  # Task 25: always draft, save via proposal
            activity_report_id=linked_report_id,
        )
        output = ActivityReportOrchestrator(self.db).run(orch_input)

        from app.services.assistant_action_service import create_action_proposal

        proposal = create_action_proposal(
            self.db,
            action_type="activity_report_generate",
            source="activity_detail" if inp.activity_id else "assistant",
            activity_id=linked_report_id,
            payload={
                "activity_report_id": str(linked_report_id) if linked_report_id else None,
                "title": output.title,
                "content": output.content,
                "summary": output.summary,
                "category_id": str(category_id),
            },
            preview={
                "title": output.title,
                "summary": (output.summary or "")[:200],
            },
            confidence=output.confidence,
            risk_level="low",
        )

        result_dict = {
            "title": output.title,
            "summary": output.summary,
            "content": output.content,
            "missing_fields": output.missing_fields,
            "confidence": output.confidence,
            "model": output.model,
            "saved": False,
            "activity_report_id": str(output.activity_report_id) if output.activity_report_id else None,
            "action_id": str(proposal.id),
            "proposal_status": proposal.status,
        }

        activity_msg = ""
        if activity_res.mode == "linked" and activity_res.activity_title:
            activity_msg = f" ({activity_res.activity_title} 활동에 연결)"

        msg = f"활동 보고서 초안이 생성되었습니다: '{output.title}'{activity_msg}. 확인 후 반영을 눌러야 저장됩니다."

        detail_url = f"/activities/{activity_res.activity_id}" if activity_res.mode == "linked" and activity_res.activity_id else "/reports"

        return AssistantExecuteResponse(
            intent="activity_report_generate",
            confidence=ir.confidence,
            agent_flow=["IntentRouter", "FileParser", "PostAgent", "PublisherAgent"],
            result_type="activity_report_draft",
            result=result_dict,
            requires_confirmation=True,
            message=msg,
            apply_payload={"action_id": str(proposal.id)},
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
        from app.models.activity import ActivityParticipant
        from app.services.assistant_action_service import (
            create_action_proposal,
            preview_activity_fee_generate_action,
        )

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

        preview = preview_activity_fee_generate_action(
            self.db,
            activity_id=activity_uuid,
            fee_amount=fee_amount,
        )
        proposal = create_action_proposal(
            self.db,
            action_type="activity_fee_generate",
            source="activity_detail" if inp.activity_id else "assistant",
            activity_id=activity_uuid,
            payload={
                "activity_id": str(activity_uuid),
                "fee_amount": fee_amount,
                "message": inp.message or "",
            },
            preview=preview,
            confidence=ir.confidence,
            risk_level="medium",
        )

        result_dict = {
            "activity_id": activity_res.activity_id,
            "activity_title": activity_res.activity_title,
            "fee_amount": fee_amount,
            "period_key": preview["period_key"],
            "created_count": preview["created_count"],
            "updated_count": preview["updated_count"],
            "changed_amount_count": preview["changed_amount_count"],
            "total_participants": len(participants),
            "action_id": str(proposal.id),
            "proposal_status": proposal.status,
        }

        return AssistantExecuteResponse(
            intent="activity_fee_generate",
            confidence=ir.confidence,
            agent_flow=["Activity Resolver", "Budget Agent", "Publisher Agent"],
            result_type="activity_fee_generation_result",
            result=result_dict,
            requires_confirmation=True,
            apply_payload={"action_id": str(proposal.id)},
            message=f"참여자 {len(participants)}명 기준 활동비 {fee_amount:,}원 납부 대상 생성을 제안했습니다. 확인 후 반영을 눌러야 저장됩니다.",
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
    # payment_manual_update (Task 23)
    # ------------------------------------------------------------------

    def _payment_manual_update(
        self,
        inp: AssistantInput,
        ir: IntentResult,
        activity_res: ActivityResolutionResult,
    ) -> AssistantExecuteResponse:
        """Handle manual payment status changes like '박민서가 15000원 냈어'."""
        from app.services.assistant_action_service import create_action_proposal
        from app.services.payment_manual_update_service import apply_manual_payment_update

        explicit_payment_type = _infer_payment_type_from_text(inp.message)

        # Global generic payment verbs are intentionally ambiguous. Do not infer
        # membership_fee/activity_fee from "냈어", "완납 처리" alone.
        if activity_res.mode != "linked" or not activity_res.activity_id:
            if explicit_payment_type == "activity_fee":
                message = "활동비 납부 상태를 변경하려면 활동 상세 페이지에서 AI 작업을 실행해 주세요."
                detail_url = "/activities"
            elif explicit_payment_type == "membership_fee":
                message = "회비 납부 상태 변경은 Payments 회비 탭 문맥에서 처리해 주세요."
                detail_url = "/payments?tab=membership_fee"
            else:
                message = "회비인지 활동비인지 먼저 확인해 주세요. 전역 요청에서는 '냈어' 같은 표현만으로 납부 유형을 추정하지 않습니다."
                detail_url = "/assistant"
            return AssistantExecuteResponse(
                intent="payment_manual_update",
                confidence=ir.confidence,
                agent_flow=["Activity Resolver", "PaymentUpdateAgent"],
                result_type="general_message",
                result={
                    "payment_type": explicit_payment_type,
                    "needs_payment_type_confirmation": explicit_payment_type is None,
                },
                requires_confirmation=True,
                message=message,
                activity_context=_build_activity_context_dict(activity_res),
                detail_url=detail_url,
            )

        # In an activity detail context, generic payment-complete wording maps to
        # activity_fee. Explicit membership_fee wording is rejected instead of
        # touching activity_fee records.
        if explicit_payment_type == "membership_fee":
            return AssistantExecuteResponse(
                intent="payment_manual_update",
                confidence=ir.confidence,
                agent_flow=["Activity Resolver", "PaymentUpdateAgent"],
                result_type="general_message",
                result={
                    "payment_type": "membership_fee",
                    "blocked_payment_type": "activity_fee",
                },
                requires_confirmation=True,
                message="현재 활동 상세 문맥에서는 활동비만 수정합니다. 회비 변경은 Payments 회비 탭에서 처리해 주세요.",
                activity_context=_build_activity_context_dict(activity_res),
                detail_url="/payments?tab=membership_fee",
            )

        try:
            activity_uuid = UUID(activity_res.activity_id)
        except (ValueError, AttributeError):
            return AssistantExecuteResponse(
                intent="payment_manual_update",
                confidence=ir.confidence,
                agent_flow=["Activity Resolver", "PaymentUpdateAgent"],
                result_type="error",
                result={"error": "Invalid activity_id"},
                requires_confirmation=False,
                message="활동 ID가 올바르지 않습니다.",
                detail_url="/activities",
            )

        payment_type = "activity_fee"
        result = apply_manual_payment_update(
            db=self.db,
            activity_id=activity_uuid,
            message=inp.message or "",
            payment_type=payment_type,
            dry_run=True,
        )

        result_dict: dict = {
            "member_name": result.member_name,
            "payment_type": result.payment_type,
            "payment_type_label": _payment_type_label(result.payment_type),
            "activity_id": result.activity_id,
            "activity_title": result.activity_title,
            "required_amount": result.required_amount,
            "previous_paid_amount": result.previous_paid_amount,
            "new_paid_amount": result.new_paid_amount,
            "previous_status": result.previous_status,
            "new_status": result.new_status,
            "payment_record_id": result.payment_record_id,
        }

        if result.candidates:
            result_dict["candidates"] = result.candidates

        detail_url = f"/activities/{result.activity_id}" if result.activity_id else "/payments?tab=activity_fee"

        if result.ok:
            proposal = create_action_proposal(
                self.db,
                action_type="payment_manual_update",
                source="activity_detail" if inp.activity_id else "assistant",
                activity_id=activity_uuid,
                payload={
                    "activity_id": str(activity_uuid),
                    "message": inp.message or "",
                    "payment_type": payment_type,
                },
                preview=result_dict,
                confidence=ir.confidence,
                risk_level="low",
            )
            result_dict["action_id"] = str(proposal.id)
            result_dict["proposal_status"] = proposal.status

        return AssistantExecuteResponse(
            intent="payment_manual_update",
            confidence=ir.confidence,
            agent_flow=["Activity Resolver", "PaymentUpdateAgent"],
            result_type="payment_manual_update_result",
            result=result_dict,
            requires_confirmation=True if result.ok else result.requires_confirmation,
            apply_payload={"action_id": result_dict["action_id"]} if result.ok else None,
            message=(
                f"{_payment_type_label(result.payment_type)} 납부 상태 변경 예정: {result.message} 확인 후 반영을 눌러야 저장됩니다."
                if result.ok else result.message
            ),
            activity_context={
                "mode": "current_activity" if result.ok else "linked",
                "activity_id": result.activity_id,
                "activity_title": result.activity_title,
                "confidence": 1.0,
            },
            detail_url=detail_url,
        )

    # ------------------------------------------------------------------
    # activity_fee_transaction_match (Task 30)
    # ------------------------------------------------------------------

    def _activity_fee_transaction_match(
        self,
        inp: AssistantInput,
        ir: IntentResult,
        activity_res: ActivityResolutionResult,
    ) -> AssistantExecuteResponse:
        """Match bank transactions against this activity's activity_fee records.

        Requires activity_id to be linked. Without it, returns clarification.
        Never applies automatically — always requires user confirmation.
        """
        from app.services.activity_fee_transaction_matching_service import (
            preview_activity_fee_transaction_matching,
        )

        # Without activity_id: ask user which activity
        if activity_res.mode != "linked" or not activity_res.activity_id:
            return AssistantExecuteResponse(
                intent="activity_fee_transaction_match",
                confidence=ir.confidence,
                agent_flow=["Activity Resolver", "ActivityFeeMatchService"],
                result_type="general_message",
                result={},
                requires_confirmation=True,
                message="어떤 활동의 활동비를 매칭할까요? 활동 상세 페이지의 활동비 탭에서 실행해 주세요.",
                activity_context=_build_activity_context_dict(activity_res),
                activity_candidates=_build_candidates_list(activity_res),
                detail_url="/activities",
            )

        try:
            activity_uuid = UUID(activity_res.activity_id)
        except (ValueError, AttributeError):
            return AssistantExecuteResponse(
                intent="activity_fee_transaction_match",
                confidence=ir.confidence,
                agent_flow=["Activity Resolver"],
                result_type="error",
                result={"error": "Invalid activity_id"},
                requires_confirmation=False,
                message="활동 ID가 올바르지 않습니다.",
                detail_url="/activities",
            )

        try:
            preview = preview_activity_fee_transaction_matching(db=self.db, activity_id=activity_uuid)
        except Exception as exc:
            logger.exception("activity_fee_transaction_match preview error: %s", exc)
            return AssistantExecuteResponse(
                intent="activity_fee_transaction_match",
                confidence=ir.confidence,
                agent_flow=["Activity Resolver", "ActivityFeeMatchService"],
                result_type="error",
                result={"error": str(exc)},
                requires_confirmation=False,
                message=f"활동비 매칭 분석 중 오류: {exc}",
                detail_url=f"/activities/{activity_res.activity_id}",
            )

        s = preview.summary
        msg = (
            f"활동비 거래내역 매칭 미리보기:\n"
            f"자동 매칭 후보 {s.auto_match_candidates}건 · "
            f"금액 불일치 {s.amount_mismatch}건 · "
            f"이름 확인 필요 {s.name_check_required}건\n"
            f"확인 후 반영하시겠습니까?"
        )

        return AssistantExecuteResponse(
            intent="activity_fee_transaction_match",
            confidence=ir.confidence,
            agent_flow=["Activity Resolver", "ActivityFeeMatchService"],
            result_type="activity_fee_transaction_match_preview",
            result={
                "activity_id": preview.activity_id,
                "action_id": preview.action_id,
                "summary": {
                    "auto_match_candidates": s.auto_match_candidates,
                    "amount_mismatch": s.amount_mismatch,
                    "name_check_required": s.name_check_required,
                    "already_paid": s.already_paid,
                    "unmatched": s.unmatched,
                },
                "rows": [
                    {
                        "memo": r.memo,
                        "deposit_amount": r.deposit_amount,
                        "matched_member_name": r.matched_member_name,
                        "required_amount": r.required_amount,
                        "match_status": r.match_status,
                        "reason": r.reason,
                    }
                    for r in preview.rows[:10]
                ],
                "requires_confirmation": True,
                "auto_apply": False,
            },
            requires_confirmation=True,
            message=msg,
            apply_payload={"action_id": preview.action_id},
            detail_url=f"/activities/{activity_res.activity_id}",
            activity_context=_build_activity_context_dict(activity_res),
        )

    # ------------------------------------------------------------------
    # bulk_membership_fee_mark_paid (Task 28)
    # ------------------------------------------------------------------

    def _bulk_membership_fee_mark_paid(
        self,
        inp: AssistantInput,
        ir: IntentResult,
    ) -> AssistantExecuteResponse:
        """Handle '전체 회비 완납 처리해줘' — preview only, never auto-apply.

        Uses each record's required_amount. Never uses a fixed 30,000 amount.
        Only modifies membership_fee records.
        """
        from app.services.bulk_membership_fee_service import preview_bulk_membership_fee_mark_paid
        from app.services.assistant_action_service import create_action_proposal

        period = inp.period

        preview = preview_bulk_membership_fee_mark_paid(db=self.db, period=period)
        s = preview.summary

        proposal = create_action_proposal(
            self.db,
            action_type="bulk_membership_fee_mark_paid",
            source="assistant",
            activity_id=None,
            payload={"period": period},
            preview={
                "period": period,
                "total_records": s.total_records,
                "new_member_count": s.new_member_count,
                "existing_member_count": s.existing_member_count,
                "executive_count": s.executive_count,
                "will_change_count": s.will_change_count,
                "already_paid_count": s.already_paid_count,
                "total_amount": s.total_amount,
            },
            confidence=ir.confidence,
            risk_level="medium",
        )

        items_preview = [
            {
                "member_name": item.member_name,
                "student_id": item.student_id,
                "required_amount": item.required_amount,
                "new_paid_amount": item.new_paid_amount,
                "new_status": item.new_status,
                "member_type": item.member_type,
                "previous_status": item.previous_status,
            }
            for item in preview.items[:20]
        ]

        result_dict = {
            "period": period,
            "summary": {
                "total_records": s.total_records,
                "new_member_count": s.new_member_count,
                "existing_member_count": s.existing_member_count,
                "executive_count": s.executive_count,
                "will_change_count": s.will_change_count,
                "already_paid_count": s.already_paid_count,
                "total_amount": s.total_amount,
            },
            "items_preview": items_preview,
            "action_id": str(proposal.id),
            "proposal_status": proposal.status,
        }

        if s.total_records == 0:
            msg = f"'{period}' 학기의 회비 납부 대상이 없습니다. 먼저 회비 납부 대상을 생성하세요."
        else:
            msg = (
                f"회비 일괄 완납 처리 미리보기 ({period}): "
                f"총 {s.total_records}명 중 변경 대상 {s.will_change_count}명. "
                f"각 부원의 회비 기준 금액으로 완납 처리됩니다. "
                f"확인 후 반영을 눌러야 적용됩니다."
            )

        return AssistantExecuteResponse(
            intent="bulk_membership_fee_mark_paid",
            confidence=ir.confidence,
            agent_flow=["IntentRouter", "BulkMembershipFeeService"],
            result_type="bulk_membership_fee_mark_paid_preview",
            result=result_dict,
            requires_confirmation=True,
            message=msg,
            apply_payload={"action_id": str(proposal.id)},
            detail_url="/payments",
        )

    # ------------------------------------------------------------------
    # participant_import (Task 27)
    # ------------------------------------------------------------------

    def _participant_import(
        self,
        inp: AssistantInput,
        ir: IntentResult,
        activity_res: ActivityResolutionResult,
    ) -> AssistantExecuteResponse:
        """Handle participant import request from AI assistant.

        Always returns a preview proposal — never auto-applies.
        """
        from app.services.activity_participant_import_service import preview_participant_import
        from app.models.file import UploadedFile

        if activity_res.mode != "linked" or not activity_res.activity_id:
            return AssistantExecuteResponse(
                intent="participant_import",
                confidence=ir.confidence,
                agent_flow=["Activity Resolver", "ParticipantImportService"],
                result_type="general_message",
                result={},
                requires_confirmation=True,
                message="참여자 명단을 등록하려면 활동 상세 페이지의 참여자 탭에서 실행해 주세요.",
                activity_context=_build_activity_context_dict(activity_res),
                detail_url="/activities",
            )

        if not inp.file_ids:
            return AssistantExecuteResponse(
                intent="participant_import",
                confidence=ir.confidence,
                agent_flow=["Activity Resolver", "ParticipantImportService"],
                result_type="error",
                result={"error": "No uploaded file"},
                requires_confirmation=False,
                message="참여자 명단 파일을 첨부해 주세요.",
                detail_url=f"/activities/{activity_res.activity_id}",
            )

        try:
            activity_uuid = UUID(activity_res.activity_id)
        except (ValueError, AttributeError):
            return AssistantExecuteResponse(
                intent="participant_import",
                confidence=ir.confidence,
                agent_flow=["Activity Resolver"],
                result_type="error",
                result={"error": "Invalid activity_id"},
                requires_confirmation=False,
                message="활동 ID가 올바르지 않습니다.",
                detail_url="/activities",
            )

        # Find spreadsheet file
        spreadsheet: tuple[Path, str, UUID] | None = None
        for file_id, file_name, file_path in zip(inp.file_ids, inp.file_names, inp.file_paths):
            if file_path.suffix.lower() in (".xlsx", ".xls", ".csv"):
                spreadsheet = (file_path, file_name, file_id)
                break

        if not spreadsheet:
            return AssistantExecuteResponse(
                intent="participant_import",
                confidence=ir.confidence,
                agent_flow=["Activity Resolver", "ParticipantImportService"],
                result_type="error",
                result={"error": "No spreadsheet file"},
                requires_confirmation=False,
                message="엑셀 또는 CSV 형식의 참여자 명단 파일을 첨부해 주세요.",
                detail_url=f"/activities/{activity_res.activity_id}",
            )

        file_path, file_name, file_id = spreadsheet

        try:
            preview = preview_participant_import(
                db=self.db,
                file_bytes=file_path.read_bytes(),
                filename=file_name,
                activity_id=activity_uuid,
                file_id=file_id,
            )
        except Exception as exc:
            logger.exception("participant_import preview error: %s", exc)
            return AssistantExecuteResponse(
                intent="participant_import",
                confidence=ir.confidence,
                agent_flow=["Activity Resolver", "ParticipantImportService"],
                result_type="error",
                result={"error": str(exc)},
                requires_confirmation=False,
                message=f"명단 파일 분석 중 오류: {exc}",
                detail_url=f"/activities/{activity_res.activity_id}",
            )

        summary = preview.summary
        msg_lines = [
            f"명단 파일을 분석했습니다.",
            f"기존 부원 연결: {summary.matched_members}명",
        ]
        if summary.unregistered_candidates:
            msg_lines.append(f"미등록 후보: {summary.unregistered_candidates}명")
        if summary.already_participants:
            msg_lines.append(f"이미 참가자: {summary.already_participants}명")
        if summary.duplicate_candidates:
            msg_lines.append(f"중복 후보: {summary.duplicate_candidates}명")
        msg_lines.append("확인 후 반영하시겠습니까?")
        msg = "\n".join(msg_lines)

        return AssistantExecuteResponse(
            intent="participant_import",
            confidence=ir.confidence,
            agent_flow=["Activity Resolver", "ParticipantImportService"],
            result_type="participant_import_preview",
            result={
                "activity_id": preview.activity_id,
                "action_id": preview.action_id,
                "summary": {
                    "total_rows": summary.total_rows,
                    "matched_members": summary.matched_members,
                    "unregistered_candidates": summary.unregistered_candidates,
                    "duplicate_candidates": summary.duplicate_candidates,
                    "needs_review": summary.needs_review,
                    "already_participants": summary.already_participants,
                    "will_create_participants": summary.will_create_participants,
                },
                "requires_confirmation": True,
                "auto_apply": False,
            },
            requires_confirmation=True,
            message=msg,
            apply_payload={"action_id": preview.action_id},
            detail_url=f"/activities/{activity_res.activity_id}",
            activity_context=_build_activity_context_dict(activity_res),
        )

    # ------------------------------------------------------------------
    # membership_fee_generate (Task 33)
    # ------------------------------------------------------------------

    def _membership_fee_generate(
        self,
        inp: AssistantInput,
        ir: IntentResult,
    ) -> AssistantExecuteResponse:
        """Handle '이번 학기 회비 대상 생성해줘' — direct to Payments page.

        This intent is for generating membership_fee PaymentRecord rows for all
        active members. The feature lives in the Payments page UI.
        Always membership_fee domain. Never touches activity_fee.
        """
        period = inp.period
        return AssistantExecuteResponse(
            intent="membership_fee_generate",
            confidence=ir.confidence,
            agent_flow=["IntentRouter"],
            result_type="general_message",
            result={
                "domain": "membership_fee",
                "scope": "global",
                "period": period,
                "guidance": "납부 현황 페이지에서 회비 납부 대상 생성 기능을 사용하세요.",
            },
            requires_confirmation=False,
            message=(
                f"회비 납부 대상 생성은 납부 현황 페이지에서 수행할 수 있습니다. "
                f"납부 현황 → 회비 납부 대상 생성 버튼을 사용해 주세요. "
                f"(학기: {period}, 대상: membership_fee)"
            ),
            detail_url="/payments",
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


def _infer_activity_fields(message: str, file_names: list[str]) -> ActivityFieldInference:
    return ActivityFieldInference(
        title=_infer_activity_title(message, file_names),
        activity_date=_infer_activity_date(message),
        location=_infer_activity_location(message),
        description=message or None,
    )


def _infer_activity_title(message: str, file_names: list[str]) -> str:
    for file_name in file_names:
        candidate = _infer_activity_title_from_filename(file_name)
        if candidate:
            return candidate

    quoted = re.search(r"['\"]([^'\"]{2,80})['\"]", message)
    if quoted:
        candidate = _clean_activity_title(quoted.group(1))
        if candidate:
            return candidate

    for pattern in (
        r"([가-힣A-Za-z0-9 _-]{2,60}?활동)\s*(?:만들|생성|등록)",
        r"(?:^|[.?!]\s*)([가-힣A-Za-z0-9 _-]{2,60}?활동)",
    ):
        for match in re.finditer(pattern, message):
            candidate = _clean_activity_title(match.group(1))
            if candidate:
                return candidate

    return "새 활동"


def _clean_activity_title(raw: str) -> str | None:
    text = re.sub(r"\s+", " ", raw).strip(" .,/\\_-")
    text = re.sub(r"^(?:이|이거|이 파일|이 명단|이 신청서|해당 파일|첨부 파일)\s*", "", text).strip()
    text = re.sub(r"\b[A-Z]-?\d{3,4}(?:호|실)?\b", "", text).strip()
    text = re.sub(r"\d{1,2}\s*월\s*\d{1,2}\s*일?", "", text).strip()
    text = re.sub(r"\d{1,2}\s*일\s*", "", text).strip()
    noise = (
        "명단", "파일", "신청서", "참여자", "등록", "추가", "만들", "생성",
        "진행", "예정", "A401", "활동 명단", "새 활동",
    )
    if not text or any(text == word for word in noise):
        return None
    if "새 활동" in text and any(word in text for word in ("파일", "명단", "신청서")):
        return None
    if re.fullmatch(r"(?:새\s*)?활동", text):
        return None
    if re.fullmatch(r"\d+\s*일\s*활동", text):
        return None
    if "명단" in text and "활동" not in text:
        return None
    return text[:80]


def _infer_activity_title_from_filename(file_name: str) -> str | None:
    stem = Path(file_name).stem
    text = re.sub(r"\([^)]*(?:응답|response|responses)[^)]*\)", " ", stem, flags=re.IGNORECASE)
    text = re.sub(r"(?i)(google\s*forms?|구글폼|응답|responses?|신청서|명단|모집|roster|application|feedback)", " ", text)
    text = re.sub(r"활동지", "활동", text)
    text = re.sub(r"(?<!\d)(?:20)?\d{2}\s*[-_]\s*\d\s*", " ", text)
    text = re.sub(r"\d{1,2}\s*월\s*\d{1,2}\s*일?", " ", text)
    text = re.sub(r"\d{1,2}\.\d{1,2}", " ", text)
    text = re.sub(r"[_()\[\]-]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    matches = re.findall(r"([가-힣A-Za-z0-9 ]{2,50}?활동)", text)
    if matches:
        candidate = _clean_activity_title(matches[-1])
        if candidate:
            return candidate
    candidate = _clean_activity_title(text)
    if candidate:
        if "활동" not in candidate:
            candidate = f"{candidate} 활동"
        return candidate[:80]
    return None


def _infer_activity_date(message: str) -> date | None:
    iso_match = re.search(r"(20\d{2})[-./](\d{1,2})[-./](\d{1,2})", message)
    if iso_match:
        try:
            return date(int(iso_match.group(1)), int(iso_match.group(2)), int(iso_match.group(3)))
        except ValueError:
            return None

    month_day = re.search(r"(\d{1,2})\s*월\s*(\d{1,2})\s*일?", message)
    if month_day:
        today = date.today()
        try:
            return date(today.year, int(month_day.group(1)), int(month_day.group(2)))
        except ValueError:
            return None
    if "내일" in message:
        return date.today() + timedelta(days=1)
    if "오늘" in message:
        return date.today()
    return None


def _infer_activity_location(message: str) -> str | None:
    match = re.search(r"(?<![A-Za-z0-9])([A-Z]-?\d{3,4})(?:호|실)?(?=[^A-Za-z0-9]|$)", message, flags=re.IGNORECASE)
    if match:
        return match.group(1).upper().replace("-", "")
    room_match = re.search(r"([가-힣A-Za-z0-9]+관)\s*(\d{3,4})(?:호|실)?", message)
    if room_match:
        return f"{room_match.group(1)} {room_match.group(2)}호"
    return None


def _apply_form_file_category(record, form_type: str) -> None:
    category_map = {
        "activity_application_form": ("google_form_application", "source"),
        "activity_feedback_form": ("google_form_feedback", "source"),
        "member_roster": ("member_roster", "source"),
    }
    category = category_map.get(form_type)
    if not category:
        return
    record.file_category, record.file_role = category
    record.file_type = record.file_category


def _import_risk_reasons(preview) -> list[str]:
    """Return reasons that should BLOCK automatic import.

    "ambiguous member matches" (needs_review > 0) is intentionally NOT a blocker:
    apply_import already handles ambiguous rows via upsert logic.
    Only unknown Excel headers block auto-import.
    """
    reasons: list[str] = []
    if preview.form_type == "unknown_excel":
        reasons.append("unknown excel headers")
    return reasons


def _import_row_to_dict(row) -> dict:
    return {
        "row_index": row.row_index,
        "name": row.name,
        "student_id": row.student_id,
        "phone": row.phone,
        "email": row.email,
        "department": row.department,
        "submitted_at": row.submitted_at,
        "member_match_status": row.member_match_status,
        "member_id": row.member_id,
        "participant_action": row.participant_action,
        "participant_status": row.participant_status,
        "raw_response": row.raw_response,
    }


def _extract_activity_fee_amount(message: str) -> int | None:
    if not message:
        return None

    fee_context = any(word in message for word in ("활동비", "참가비", "회비", "받을", "받을거", "받을거야", "걷"))

    manwon = re.search(r"(?:(\d+)|([일이삼사오육칠팔구십한두세네]))?\s*만\s*원", message)
    if manwon and fee_context:
        if manwon.group(1):
            return int(manwon.group(1)) * 10000
        if manwon.group(2):
            return _korean_small_number(manwon.group(2)) * 10000
        return 10000

    amount_with_won = re.search(r"(\d{1,3}(?:,\d{3})+|\d{4,})\s*원", message)
    if amount_with_won:
        return int(amount_with_won.group(1).replace(",", ""))

    if fee_context:
        bare_amount = re.search(r"(\d{1,3}(?:,\d{3})+|\d{4,})", message)
        if bare_amount:
            return int(bare_amount.group(1).replace(",", ""))
    return None


def _korean_small_number(raw: str) -> int:
    values = {
        "일": 1, "한": 1,
        "이": 2, "두": 2,
        "삼": 3, "세": 3,
        "사": 4, "네": 4,
        "오": 5,
        "육": 6,
        "칠": 7,
        "팔": 8,
        "구": 9,
        "십": 10,
    }
    return values.get(raw, 1)


def _create_activity_fee_records(db: Session, activity_id: UUID, amount: int) -> dict:
    from app.models.activity import ActivityParticipant
    from app.models.payment import PaymentRecord

    participants = list(
        db.scalars(
            select(ActivityParticipant).where(ActivityParticipant.activity_report_id == activity_id)
        )
    )
    period_key = f"act-{str(activity_id)[:8]}"
    created = 0
    updated = 0

    for participant in participants:
        existing = db.scalar(
            select(PaymentRecord).where(
                and_(
                    PaymentRecord.member_id == participant.member_id,
                    PaymentRecord.period == period_key,
                    PaymentRecord.payment_type == "activity_fee",
                )
            )
        )
        if existing:
            if existing.status not in ("paid", "partial", "exempt", "refunded"):
                existing.required_amount = amount
                updated += 1
            continue

        db.add(
            PaymentRecord(
                member_id=participant.member_id,
                period=period_key,
                payment_type="activity_fee",
                required_amount=amount,
                paid_amount=0,
                status="unpaid",
                activity_report_id=activity_id,
            )
        )
        created += 1

    db.flush()
    return {
        "amount": amount,
        "created_count": created,
        "updated_count": updated,
        "total_participants": len(participants),
        "payment_type": "activity_fee",
        "period_key": period_key,
    }


def _extract_amount(message: str) -> int | None:
    """Extract a monetary amount (KRW) from a message string."""
    activity_fee_amount = _extract_activity_fee_amount(message)
    if activity_fee_amount:
        return activity_fee_amount
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
