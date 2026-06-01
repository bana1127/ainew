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
    ) -> tuple[UUID, bool]:
        from app.models.receipt import Receipt

        # Parse receipt_date
        receipt_date: date_type | None = None
        raw_date = extracted.get("receipt_date")
        if raw_date:
            try:
                receipt_date = date_type.fromisoformat(str(raw_date))
            except ValueError:
                pass

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
        )
        self.db.add(receipt)
        self.db.commit()
        self.db.refresh(receipt)
        return receipt.id, True
