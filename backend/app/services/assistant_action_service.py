from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.models.assistant_action import AssistantActionProposal

INACTIVE_PARTICIPANT_STATUSES = {"removed", "cancelled", "excluded", "deleted", "inactive"}
INACTIVE_ACTIVITY_FEE_STATUSES = {"cancelled", "excluded"}


def _active_participant_condition(ActivityParticipant, activity_id: UUID):
    return and_(
        ActivityParticipant.activity_report_id == activity_id,
        or_(
            ActivityParticipant.status.is_(None),
            ActivityParticipant.status.notin_(INACTIVE_PARTICIPANT_STATUSES),
        ),
    )


def create_action_proposal(
    db: Session,
    *,
    action_type: str,
    source: str,
    activity_id: UUID | None,
    payload: dict,
    preview: dict,
    confidence: float | None,
    risk_level: str = "medium",
) -> AssistantActionProposal:
    proposal = AssistantActionProposal(
        action_type=action_type,
        source=source,
        activity_id=activity_id,
        payload_json=payload,
        preview_json=preview,
        status="pending",
        confidence=confidence,
        risk_level=risk_level,
    )
    db.add(proposal)
    db.commit()
    db.refresh(proposal)
    return proposal


def cancel_action_proposal(db: Session, action_id: UUID) -> AssistantActionProposal:
    proposal = _get_pending_action(db, action_id)
    proposal.status = "cancelled"
    proposal.cancelled_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(proposal)
    return proposal


def confirm_action_proposal(db: Session, action_id: UUID) -> tuple[AssistantActionProposal, dict]:
    proposal = _get_pending_action(db, action_id)
    if proposal.action_type != "participant_import":
        proposal.status = "confirmed"
        proposal.confirmed_at = datetime.now(timezone.utc)

    _HANDLERS = {
        "activity_fee_generate": apply_activity_fee_generate_action,
        "payment_manual_update": apply_payment_manual_update_action,
        "bank_statement_import": apply_bank_statement_import_action,
        "payment_matching": apply_payment_matching_action,
        "membership_fee_generate": apply_membership_fee_generate_action,
        "receipt_analysis": apply_receipt_analysis_action,
        "activity_report_generate": apply_activity_report_generate_action,
        "google_form_import": apply_google_form_import_action,
        "member_import": apply_member_import_action,
        "participant_import": apply_participant_import_action,
        "bulk_membership_fee_mark_paid": apply_bulk_membership_fee_mark_paid_action,
        "activity_fee_transaction_match": apply_activity_fee_transaction_match_action,
    }

    handler = _HANDLERS.get(proposal.action_type)
    if handler is None:
        proposal.status = "failed"
        db.commit()
        raise ValueError(f"Unsupported action_type: {proposal.action_type}")

    payload = proposal.payload_json
    if proposal.action_type in ("participant_import", "activity_fee_transaction_match"):
        payload = {**(payload or {}), "action_id": str(proposal.id)}

    result = handler(db, payload)

    proposal.status = "applied"
    if proposal.confirmed_at is None:
        proposal.confirmed_at = datetime.now(timezone.utc)
    proposal.applied_at = datetime.now(timezone.utc)
    proposal.preview_json = {**(proposal.preview_json or {}), "applied_result": result}
    db.commit()
    db.refresh(proposal)
    return proposal, result


def preview_activity_fee_generate_action(
    db: Session,
    *,
    activity_id: UUID,
    fee_amount: int,
) -> dict:
    from app.models.activity import ActivityParticipant
    from app.models.payment import PaymentRecord

    participants = list(
        db.scalars(
            select(ActivityParticipant).where(_active_participant_condition(ActivityParticipant, activity_id))
        )
    )
    period_key = f"act-{str(activity_id)[:8]}"
    existing = list(
        db.scalars(
            select(PaymentRecord).where(
                and_(
                    PaymentRecord.period == period_key,
                    PaymentRecord.payment_type == "activity_fee",
                )
            )
        )
    )
    participant_member_ids = {p.member_id for p in participants if p.member_id}
    existing_for_activity = [r for r in existing if r.member_id in participant_member_ids]
    existing_member_ids = {r.member_id for r in existing_for_activity}
    changed_amount_count = sum(1 for r in existing_for_activity if r.required_amount != fee_amount)
    preserved_paid_count = sum(1 for r in existing_for_activity if r.paid_amount > 0)

    return {
        "activity_id": str(activity_id),
        "fee_amount": fee_amount,
        "period_key": period_key,
        "created_count": len(participant_member_ids - existing_member_ids),
        "updated_count": len(existing_for_activity),
        "changed_amount_count": changed_amount_count,
        "preserved_paid_count": preserved_paid_count,
        "total_participants": len(participants),
        "payment_type": "activity_fee",
    }


def apply_activity_fee_generate_action(db: Session, payload: dict) -> dict:
    from app.models.activity import ActivityParticipant
    from app.models.payment import PaymentRecord

    activity_id = UUID(str(payload["activity_id"]))
    fee_amount = int(payload["fee_amount"])
    participants = list(
        db.scalars(
            select(ActivityParticipant).where(_active_participant_condition(ActivityParticipant, activity_id))
        )
    )
    period_key = f"act-{str(activity_id)[:8]}"
    created = 0
    updated = 0
    active_member_ids = {p.member_id for p in participants if p.member_id}

    for participant in participants:
        if not participant.member_id:
            continue
        record = db.scalar(
            select(PaymentRecord).where(
                and_(
                    PaymentRecord.member_id == participant.member_id,
                    PaymentRecord.period == period_key,
                    PaymentRecord.payment_type == "activity_fee",
                )
            )
        )
        if record:
            record.required_amount = fee_amount
            record.activity_report_id = activity_id
            if record.status in INACTIVE_ACTIVITY_FEE_STATUSES:
                record.refund_status = None
            if record.status not in ("exempt", "need_check"):
                record.status = _payment_status(record.paid_amount, fee_amount)
            updated += 1
            continue

        db.add(
            PaymentRecord(
                member_id=participant.member_id,
                period=period_key,
                payment_type="activity_fee",
                required_amount=fee_amount,
                paid_amount=0,
                status="unpaid",
                activity_report_id=activity_id,
            )
        )
        created += 1

    cancelled = 0
    stale_records = list(db.scalars(
        select(PaymentRecord).where(
            and_(
                PaymentRecord.period == period_key,
                PaymentRecord.payment_type == "activity_fee",
                PaymentRecord.activity_report_id == activity_id,
            )
        )
    ))
    for record in stale_records:
        if record.member_id in active_member_ids or record.status in INACTIVE_ACTIVITY_FEE_STATUSES:
            continue
        record.status = "cancelled"
        if (record.paid_amount or 0) > 0:
            record.refund_status = "refund_required"
        cancelled += 1

    db.flush()
    return {
        "activity_id": str(activity_id),
        "fee_amount": fee_amount,
        "period_key": period_key,
        "created_count": created,
        "updated_count": updated,
        "cancelled_count": cancelled,
        "total_participants": len(participants),
    }


def apply_payment_manual_update_action(db: Session, payload: dict) -> dict:
    from app.services.payment_manual_update_service import apply_manual_payment_update

    payment_type = str(payload.get("payment_type") or "activity_fee")
    if payment_type != "activity_fee":
        raise ValueError("payment_manual_update action only supports activity_fee")

    result = apply_manual_payment_update(
        db=db,
        activity_id=UUID(str(payload["activity_id"])),
        message=str(payload.get("message") or ""),
        payment_type=payment_type,
    )
    return {
        "ok": result.ok,
        "member_name": result.member_name,
        "payment_type": result.payment_type,
        "activity_id": result.activity_id,
        "activity_title": result.activity_title,
        "required_amount": result.required_amount,
        "previous_paid_amount": result.previous_paid_amount,
        "new_paid_amount": result.new_paid_amount,
        "previous_status": result.previous_status,
        "new_status": result.new_status,
        "payment_record_id": result.payment_record_id,
        "message": result.message,
    }


def apply_bank_statement_import_action(db: Session, payload: dict) -> dict:
    from app.models import BankTransaction
    from app.models.file import UploadedFile
    from app.services.bank_statement_parser import parse_bank_statement
    from app.core.config import settings

    file_id_str = payload.get("file_id")
    if not file_id_str:
        raise ValueError("file_id is required")

    file_record = db.get(UploadedFile, UUID(file_id_str))
    if not file_record or not file_record.stored_filename:
        raise ValueError("Uploaded file not found")

    abs_path = settings.UPLOAD_DIR / file_record.stored_filename
    parsed = parse_bank_statement(abs_path)

    existing_keys: set[tuple] = set()
    for row in db.execute(select(BankTransaction)).scalars().all():
        existing_keys.add((
            str(row.transaction_datetime), row.memo,
            row.withdraw_amount, row.deposit_amount, row.balance,
        ))

    inserted = 0
    duplicates = 0
    for tx in parsed.transactions:
        key = (str(tx.transaction_datetime), tx.memo, tx.withdraw_amount, tx.deposit_amount, tx.balance)
        if key in existing_keys:
            duplicates += 1
            continue
        db.add(BankTransaction(
            transaction_datetime=tx.transaction_datetime,
            transaction_type=tx.transaction_type,
            memo=tx.memo,
            withdraw_amount=tx.withdraw_amount,
            deposit_amount=tx.deposit_amount,
            balance=tx.balance,
            branch=tx.branch,
            match_status="unmatched",
        ))
        existing_keys.add(key)
        inserted += 1

    db.flush()
    return {
        "inserted_rows": inserted,
        "duplicate_rows": duplicates,
        "total_rows": parsed.total_rows,
        "parsed_rows": parsed.parsed_rows,
    }


def apply_payment_matching_action(db: Session, payload: dict) -> dict:
    from app.services.payment_matching_service import apply_payment_matching

    payment_type = str(payload["payment_type"])
    if payment_type not in {"membership_fee", "activity_fee"}:
        raise ValueError("payment_type must be membership_fee or activity_fee")

    result = apply_payment_matching(
        db=db,
        period=str(payload["period"]),
        payment_type=payment_type,
        required_amount=int(payload["required_amount"]),
    )
    return {
        "period": result.period,
        "payment_type": result.payment_type,
        "matched_count": result.matched_count,
        "unpaid_count": result.unpaid_count,
        "created_payment_records": result.created_payment_records,
        "updated_payment_records": result.updated_payment_records,
        "updated_transactions": result.updated_transactions,
    }


def apply_membership_fee_generate_action(db: Session, payload: dict) -> dict:
    from app.services.membership_fee_policy import apply_membership_fee_generation

    return apply_membership_fee_generation(
        db=db,
        period=str(payload.get("period") or ""),
        new_member_fee=int(payload.get("new_member_fee") or 15000),
        existing_member_fee=int(payload.get("existing_member_fee") or 10000),
        executive_fee=int(payload.get("executive_fee") or 0),
    )


def apply_receipt_analysis_action(db: Session, payload: dict) -> dict:
    from datetime import date as _date
    from uuid import UUID as _UUID
    from app.models.receipt import Receipt

    file_id_str = payload.get("file_id")
    extracted = payload.get("extracted", {})
    policy = payload.get("policy", {})
    activity_report_id_str = payload.get("activity_report_id")
    activity_report_id = _UUID(activity_report_id_str) if activity_report_id_str else None

    raw_date = extracted.get("receipt_date")
    parsed_date: _date | None = None
    if raw_date:
        try:
            parsed_date = _date.fromisoformat(str(raw_date)[:10])
        except (ValueError, TypeError):
            parsed_date = None

    receipt = Receipt(
        file_id=_UUID(file_id_str) if file_id_str else None,
        activity_report_id=activity_report_id,
        receipt_date=parsed_date,
        store_name=extracted.get("store_name"),
        amount=int(extracted.get("amount") or 0),
        payment_method=extracted.get("payment_method"),
        category=extracted.get("category"),
        evidence_status=policy.get("evidence_status", "pending"),
        need_check=bool(policy.get("need_check", False)),
        reason=policy.get("reason"),
    )
    db.add(receipt)
    db.flush()
    return {
        "receipt_id": str(receipt.id),
        "store_name": receipt.store_name,
        "amount": receipt.amount,
        "evidence_status": receipt.evidence_status,
    }


def apply_activity_report_generate_action(db: Session, payload: dict) -> dict:
    from uuid import UUID as _UUID
    from app.models.activity import ActivityReport

    activity_report_id_str = payload.get("activity_report_id")
    title = str(payload.get("title", "활동 보고서"))
    content = str(payload.get("content", ""))
    summary = str(payload.get("summary", ""))

    if activity_report_id_str:
        activity_report_id = _UUID(activity_report_id_str)
        report = db.get(ActivityReport, activity_report_id)
        if report:
            report.final_content = content
            report.generated_content = content
            db.flush()
            return {
                "activity_report_id": str(report.id),
                "title": report.title,
                "saved": True,
            }

    return {"saved": False, "title": title}


def apply_google_form_import_action(db: Session, payload: dict) -> dict:
    from app.services.google_form_import_service import apply_import, ImportRow

    activity_id = str(payload["activity_id"])
    form_type = str(payload["form_type"])
    raw_rows = payload.get("rows", [])
    activity_fee_amount = payload.get("activity_fee_amount")

    rows = []
    for r in raw_rows:
        row = ImportRow(
            row_index=int(r.get("row_index", 0)),
            name=r.get("name"),
            student_id=r.get("student_id"),
            phone=r.get("phone"),
            email=r.get("email"),
            department=r.get("department"),
            submitted_at=r.get("submitted_at"),
            member_match_status=str(r.get("member_match_status", "unknown")),
            member_id=r.get("member_id"),
            participant_action=str(r.get("participant_action", "add")),
            participant_status=str(r.get("participant_status", "attended")),
            raw_response=r.get("raw_response") or {},
        )
        rows.append(row)

    result = apply_import(db=db, activity_id=activity_id, form_type=form_type, rows=rows)

    applied_result = {
        "activity_id": result.activity_id,
        "form_type": result.form_type,
        "created_members": result.created_members,
        "updated_members": result.updated_members,
        "created_participants": result.created_participants,
        "updated_participants": result.updated_participants,
    }

    if activity_fee_amount:
        from uuid import UUID as _UUID
        from app.models.activity import ActivityParticipant
        from app.models.payment import PaymentRecord
        from sqlalchemy import and_

        activity_uuid = _UUID(activity_id)
        participants = list(db.scalars(
            select(ActivityParticipant).where(ActivityParticipant.activity_report_id == activity_uuid)
        ))
        period_key = f"act-{str(activity_uuid)[:8]}"
        fee_created = 0
        for p in participants:
            existing = db.scalar(
                select(PaymentRecord).where(
                    and_(
                        PaymentRecord.member_id == p.member_id,
                        PaymentRecord.period == period_key,
                        PaymentRecord.payment_type == "activity_fee",
                    )
                )
            )
            if not existing:
                db.add(PaymentRecord(
                    member_id=p.member_id,
                    period=period_key,
                    payment_type="activity_fee",
                    required_amount=int(activity_fee_amount),
                    paid_amount=0,
                    status="unpaid",
                    activity_report_id=activity_uuid,
                ))
                fee_created += 1
        db.flush()
        applied_result["activity_fee_created"] = fee_created
        applied_result["activity_fee_amount"] = int(activity_fee_amount)

    return applied_result


def apply_member_import_action(db: Session, payload: dict) -> dict:
    from app.services.member_import_service import apply_member_import_action as svc_apply
    return svc_apply(db, payload)


def apply_participant_import_action(db: Session, payload: dict) -> dict:
    """Apply participant import via the service layer (used when action_id-based confirm is called)."""
    from app.services.activity_participant_import_service import confirm_participant_import
    from uuid import UUID as _UUID

    action_id_str = payload.get("action_id")
    if not action_id_str:
        raise ValueError("action_id is required in participant_import payload")

    row_overrides = payload.get("row_overrides") or []
    result = confirm_participant_import(
        db=db,
        action_id=_UUID(action_id_str),
        row_overrides=row_overrides,
    )
    return {
        "ok": result.ok,
        "activity_id": result.activity_id,
        "created_participants": result.created_participants,
        "updated_participants": result.updated_participants,
        "already_participants": result.already_participants,
        "external_participants": result.external_participants,
        "ignored_rows": result.ignored_rows,
        "created_members": result.created_members,
    }


def apply_activity_fee_transaction_match_action(db: Session, payload: dict) -> dict:
    from app.services.activity_fee_transaction_matching_service import (
        apply_activity_fee_transaction_match_action as svc_apply,
    )
    return svc_apply(db, payload)


def apply_bulk_membership_fee_mark_paid_action(db: Session, payload: dict) -> dict:
    """Apply bulk membership fee mark paid.

    Uses each record's required_amount — never a fixed amount.
    Only modifies membership_fee records.
    """
    from app.services.bulk_membership_fee_service import apply_bulk_membership_fee_mark_paid

    period = str(payload["period"])
    result = apply_bulk_membership_fee_mark_paid(db=db, period=period)
    return {
        "ok": result.ok,
        "period": result.period,
        "updated_count": result.updated_count,
        "skipped_count": result.skipped_count,
    }


def _get_pending_action(db: Session, action_id: UUID) -> AssistantActionProposal:
    proposal = db.get(AssistantActionProposal, action_id)
    if proposal is None:
        raise ValueError("Action proposal not found")
    if proposal.status != "pending":
        raise ValueError(f"Action proposal is not pending: {proposal.status}")
    return proposal


def _payment_status(paid: int, required: int) -> str:
    paid = max(0, int(paid or 0))
    required = max(0, int(required or 0))
    if required == 0:
        return "exempt"
    if paid == 0:
        return "unpaid"
    if paid < required:
        return "partial"
    if paid == required:
        return "paid"
    return "overpaid"
