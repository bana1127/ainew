from __future__ import annotations
from datetime import date as date_type
from uuid import UUID
from sqlalchemy.orm import Session
from app.models.activity import ActivityReport


class PublisherAgent:
    def __init__(self, db: Session):
        self.db = db

    def publish(
        self,
        activity_report_id: UUID | None,
        category_id: UUID,
        title: str,
        activity_date: str | None,
        location: str | None,
        input_text: str | None,
        generated_content: str,
    ) -> tuple[UUID, bool]:
        # Parse date
        parsed_date: date_type | None = None
        if activity_date:
            try:
                parsed_date = date_type.fromisoformat(activity_date)
            except ValueError:
                pass

        if activity_report_id is not None:
            # Update existing report
            report = self.db.get(ActivityReport, activity_report_id)
            if report is not None:
                report.generated_content = generated_content
                report.status = "generated"
                self.db.commit()
                self.db.refresh(report)
                return report.id, True

        # Create new report
        report = ActivityReport(
            category_id=category_id,
            title=title,
            activity_date=parsed_date,
            location=location,
            input_text=input_text,
            generated_content=generated_content,
            status="generated",
        )
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        return report.id, True

    def publish_receipt(
        self,
        file_id: UUID,
        activity_report_id: UUID | None,
        extracted: dict,
        evidence_status: str,
        need_check: bool,
        reason: str,
        document_type: str = "unknown",
    ) -> tuple[UUID, bool]:
        from app.models.receipt import Receipt
        from app.models.file import UploadedFile
        from app.services.evidence_parser_service import (
            detect_document_type_from_text,
            policy_for_document_type,
        )

        # Auto-detect document_type from raw_text if still unknown
        raw_text = extracted.get("raw_text") or ""
        if document_type in ("unknown", "auto", None):
            detected = detect_document_type_from_text(raw_text)
            document_type = detected if detected != "unknown" else document_type

        # Override policy for non-receipt document types (business_registration, bankbook_copy)
        amount_val = int(extracted.get("amount", 0))
        if document_type in ("business_registration", "bankbook_copy"):
            evidence_status, need_check, reason = policy_for_document_type(document_type, amount_val)
        elif document_type == "unknown" and evidence_status == "need_check" and amount_val <= 0:
            # Still unknown, but no amount: keep as pending rather than need_check for unknown docs
            pass

        # Parse receipt_date
        receipt_date: date_type | None = None
        raw_date = extracted.get("receipt_date")
        if raw_date:
            try:
                receipt_date = date_type.fromisoformat(str(raw_date))
            except ValueError:
                pass

        parsed_data = {
            k: v for k, v in extracted.items()
            if k not in ("receipt_date", "raw_text")
        }
        # Also store raw_text in parsed_data for reference
        if raw_text:
            parsed_data["raw_text_preview"] = raw_text[:500]

        receipt = Receipt(
            file_id=file_id,
            activity_report_id=activity_report_id,
            receipt_date=receipt_date,
            store_name=extracted.get("store_name"),
            amount=int(extracted.get("amount", 0)),
            payment_method=extracted.get("payment_method", "unknown"),
            category=extracted.get("category"),
            evidence_status=evidence_status,
            need_check=need_check,
            reason=reason,
            document_type=document_type,
            parsed_data=parsed_data,
        )
        self.db.add(receipt)
        self.db.flush()  # get receipt.id before commit

        # Task 43: Sync UploadedFile so it appears in the activity file vault
        if file_id:
            uploaded_file = self.db.get(UploadedFile, file_id)
            if uploaded_file:
                uploaded_file.file_category = "evidence"
                uploaded_file.file_role = "evidence"
                if activity_report_id:
                    uploaded_file.activity_report_id = activity_report_id
                    uploaded_file.related_entity_type = "activity_report"
                    uploaded_file.related_entity_id = activity_report_id

        self.db.commit()
        self.db.refresh(receipt)
        return receipt.id, True
