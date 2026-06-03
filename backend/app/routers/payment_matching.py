from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import BankTransaction, Member, PaymentRecord
from app.models.setting import AppSetting
from app.routers.common import commit_or_400, get_or_404
from app.schemas import PaymentRecordRead
from app.schemas.payment_matching import (
    MemberSummarySchema,
    PaymentConfirmPayload,
    PaymentExcludePayload,
    PaymentMatchingPayload,
    PaymentMatchingPreviewSchema,
    PaymentMatchingResultSchema,
    PaymentSummaryResponse,
    TransactionMatchItemSchema,
    UnpaidPaymentItem,
)
from app.schemas.membership_fee import (
    MembershipFeePreviewPayload,
    MembershipFeePreviewResponse,
    MembershipFeePreviewRow,
    MembershipFeePreviewSummary,
)
from app.services.membership_fee_policy import preview_membership_fee_generation
from app.services.payment_matching_service import (
    MemberSummary,
    PaymentMatchingPreview,
    PaymentMatchingResult,
    TransactionMatchItem,
    apply_payment_matching,
    preview_payment_matching,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Dataclass -> Schema conversion helpers
# ---------------------------------------------------------------------------

def _transaction_item_to_schema(item: TransactionMatchItem) -> TransactionMatchItemSchema:
    return TransactionMatchItemSchema(
        transaction_id=item.transaction_id,
        transaction_datetime=item.transaction_datetime,
        memo=item.memo,
        deposit_amount=item.deposit_amount,
        matched_member_id=item.matched_member_id,
        matched_member_name=item.matched_member_name,
        payment_type=item.payment_type,
        match_status=item.match_status,
        score=item.score,
        reason=item.reason,
        activity_id=item.activity_id,
        activity_title=item.activity_title,
        match_mode=item.match_mode,
        expected_amount=item.expected_amount,
        amount_difference=item.amount_difference,
        amount_status=item.amount_status,
        auto_match=item.auto_match,
        fee_tier=item.fee_tier,
    )


def _member_summary_to_schema(ms: MemberSummary) -> MemberSummarySchema:
    return MemberSummarySchema(
        member_id=ms.member_id,
        name=ms.name,
        student_id=ms.student_id,
        department=ms.department,
        required_amount=ms.required_amount,
        paid_amount=ms.paid_amount,
        status=ms.status,
    )


def _preview_to_schema(preview: PaymentMatchingPreview) -> PaymentMatchingPreviewSchema:
    return PaymentMatchingPreviewSchema(
        period=preview.period,
        payment_type=preview.payment_type,
        required_amount=preview.required_amount,
        total_active_members=preview.total_active_members,
        total_deposit_transactions=preview.total_deposit_transactions,
        matched_count=preview.matched_count,
        need_check_count=preview.need_check_count,
        excluded_count=preview.excluded_count,
        unpaid_count=preview.unpaid_count,
        matched_items=[_transaction_item_to_schema(i) for i in preview.matched_items],
        need_check_items=[_transaction_item_to_schema(i) for i in preview.need_check_items],
        excluded_items=[_transaction_item_to_schema(i) for i in preview.excluded_items],
        unpaid_members=[_member_summary_to_schema(m) for m in preview.unpaid_members],
    )


def _result_to_schema(result: PaymentMatchingResult) -> PaymentMatchingResultSchema:
    return PaymentMatchingResultSchema(
        period=result.period,
        payment_type=result.payment_type,
        required_amount=result.required_amount,
        total_active_members=result.total_active_members,
        total_deposit_transactions=result.total_deposit_transactions,
        matched_count=result.matched_count,
        need_check_count=result.need_check_count,
        excluded_count=result.excluded_count,
        unpaid_count=result.unpaid_count,
        matched_items=[_transaction_item_to_schema(i) for i in result.matched_items],
        need_check_items=[_transaction_item_to_schema(i) for i in result.need_check_items],
        excluded_items=[_transaction_item_to_schema(i) for i in result.excluded_items],
        unpaid_members=[_member_summary_to_schema(m) for m in result.unpaid_members],
        created_payment_records=result.created_payment_records,
        updated_payment_records=result.updated_payment_records,
        updated_transactions=result.updated_transactions,
    )


def _membership_fee_preview_to_schema(preview, action_id: str | None = None) -> MembershipFeePreviewResponse:
    return MembershipFeePreviewResponse(
        period=preview.period,
        payment_type=preview.payment_type,
        current_term=preview.current_term,
        new_member_fee=preview.new_member_fee,
        existing_member_fee=preview.existing_member_fee,
        executive_fee=preview.executive_fee,
        requires_confirmation=True,
        auto_apply=False,
        action_id=action_id,
        summary=MembershipFeePreviewSummary(
            total_members=preview.summary.total_members,
            current_term=preview.summary.current_term,
            new_member_count=preview.summary.new_member_count,
            existing_member_count=preview.summary.existing_member_count,
            executive_count=preview.summary.executive_count,
            total_required_amount=preview.summary.total_required_amount,
            total_paid_amount=preview.summary.total_paid_amount,
            created_count=preview.summary.created_count,
            updated_count=preview.summary.updated_count,
            preserved_paid_count=preview.summary.preserved_paid_count,
        ),
        rows=[
            MembershipFeePreviewRow(
                member_id=str(row.member_id),
                member_name=row.member_name,
                student_id=row.student_id,
                department=row.department,
                joined_term=row.joined_term,
                term_code=row.term_code,
                current_term=row.current_term,
                is_officer=row.is_officer,
                officer_role=row.officer_role,
                role_label=row.role_label,
                fee_tier=row.fee_tier,
                required_amount=row.required_amount,
                paid_amount=row.paid_amount,
                status=row.status,
                fee_rule_reason=row.fee_rule_reason,
                existing_record_id=str(row.existing_record_id) if row.existing_record_id else None,
                action=row.action,
            )
            for row in preview.rows
        ],
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/match-preview", response_model=PaymentMatchingPreviewSchema)
def match_preview(
    payload: PaymentMatchingPayload,
    db: Session = Depends(get_db),
) -> PaymentMatchingPreviewSchema:
    preview = preview_payment_matching(
        db=db,
        period=payload.period,
        payment_type=payload.payment_type,
        required_amount=payload.required_amount,
        start_date=payload.start_date,
        end_date=payload.end_date,
        match_mode=payload.match_mode,
        activity_id=payload.activity_id,
    )
    return _preview_to_schema(preview)


@router.post("/match-apply", response_model=PaymentMatchingResultSchema)
def match_apply(
    payload: PaymentMatchingPayload,
    db: Session = Depends(get_db),
) -> PaymentMatchingResultSchema:
    result = apply_payment_matching(
        db=db,
        period=payload.period,
        payment_type=payload.payment_type,
        required_amount=payload.required_amount,
        start_date=payload.start_date,
        end_date=payload.end_date,
        match_mode=payload.match_mode,
        activity_id=payload.activity_id,
    )
    return _result_to_schema(result)


@router.post("/membership-fees/preview", response_model=MembershipFeePreviewResponse)
def membership_fee_preview(
    payload: MembershipFeePreviewPayload,
    db: Session = Depends(get_db),
) -> MembershipFeePreviewResponse:
    preview = preview_membership_fee_generation(
        db=db,
        period=payload.period,
        new_member_fee=payload.new_member_fee,
        existing_member_fee=payload.existing_member_fee,
        executive_fee=payload.executive_fee,
    )
    from app.services.assistant_action_service import create_action_proposal

    proposal = create_action_proposal(
        db,
        action_type="membership_fee_generate",
        source="payments_page",
        activity_id=None,
        payload={
            "period": preview.current_term,
            "new_member_fee": payload.new_member_fee,
            "existing_member_fee": payload.existing_member_fee,
            "executive_fee": payload.executive_fee,
        },
        preview={
            "current_term": preview.current_term,
            "new_member_count": preview.summary.new_member_count,
            "existing_member_count": preview.summary.existing_member_count,
            "executive_count": preview.summary.executive_count,
            "total_required_amount": preview.summary.total_required_amount,
            "created_count": preview.summary.created_count,
            "updated_count": preview.summary.updated_count,
        },
        confidence=1.0,
        risk_level="medium",
    )
    return _membership_fee_preview_to_schema(preview, str(proposal.id))


@router.patch("/transactions/{transaction_id}/confirm", response_model=PaymentRecordRead)
def confirm_transaction(
    transaction_id: UUID,
    payload: PaymentConfirmPayload,
    db: Session = Depends(get_db),
) -> PaymentRecordRead:
    transaction: BankTransaction = get_or_404(db, BankTransaction, transaction_id, "BankTransaction")
    member: Member = get_or_404(db, Member, payload.member_id, "Member")

    # Upsert PaymentRecord
    existing: PaymentRecord | None = db.execute(
        select(PaymentRecord).where(
            and_(
                PaymentRecord.member_id == member.id,
                PaymentRecord.period == payload.period,
                PaymentRecord.payment_type == payload.payment_type,
            )
        )
    ).scalar_one_or_none()

    if payload.payment_type == "membership_fee":
        if existing is None:
            raise HTTPException(status_code=400, detail="membership_fee PaymentRecord is required before matching")
        duplicate_record = db.scalar(
            select(PaymentRecord).where(
                and_(
                    PaymentRecord.transaction_id == transaction.id,
                    PaymentRecord.id != existing.id,
                )
            )
        )
        if duplicate_record is not None:
            raise HTTPException(status_code=400, detail="transaction already matched to another payment record")
        if existing.status in ("paid", "exempt") or int(existing.paid_amount or 0) > 0:
            raise HTTPException(status_code=400, detail="payment record is already settled or has paid_amount")
        if int(transaction.deposit_amount or 0) != int(existing.required_amount or 0):
            raise HTTPException(status_code=400, detail="amount_mismatch")
        payload.required_amount = int(existing.required_amount or 0)
    elif payload.payment_type == "activity_fee":
        if existing is None:
            raise HTTPException(status_code=400, detail="activity_fee PaymentRecord is required before matching")
        if int(transaction.deposit_amount or 0) != int(existing.required_amount or 0):
            raise HTTPException(status_code=400, detail="amount_mismatch")
        payload.required_amount = int(existing.required_amount or 0)
    elif payload.payment_type:
        raise HTTPException(status_code=400, detail="payment_type must be membership_fee or activity_fee")

    # Update bank transaction only after validation
    transaction.matched_member_id = member.id
    transaction.payment_type = payload.payment_type
    transaction.match_status = "matched"

    if existing is not None:
        existing.paid_amount = transaction.deposit_amount
        existing.status = payload.status
        existing.transaction_id = transaction.id
        record = existing
    else:
        record = PaymentRecord(
            member_id=member.id,
            period=payload.period,
            payment_type=payload.payment_type,
            required_amount=payload.required_amount,
            paid_amount=transaction.deposit_amount,
            status=payload.status,
            transaction_id=transaction.id,
        )
        db.add(record)

    commit_or_400(db, "Failed to confirm transaction: integrity error")
    db.refresh(record)
    return PaymentRecordRead.model_validate(record)


@router.patch("/transactions/{transaction_id}/exclude")
def exclude_transaction(
    transaction_id: UUID,
    payload: PaymentExcludePayload,
    db: Session = Depends(get_db),
) -> dict:
    transaction: BankTransaction = get_or_404(db, BankTransaction, transaction_id, "BankTransaction")

    transaction.match_status = "excluded"
    transaction.payment_type = payload.payment_type

    commit_or_400(db, "Failed to exclude transaction: integrity error")

    # TODO(Task 7): Store exclusion reason in a dedicated field or log table
    return {
        "transaction_id": str(transaction.id),
        "match_status": "excluded",
        "payment_type": transaction.payment_type,
        "reason": payload.reason,
    }


@router.get("/summary", response_model=PaymentSummaryResponse)
def get_payment_summary(
    period: str = Query(...),
    payment_type: str = Query(default="membership_fee"),
    db: Session = Depends(get_db),
) -> PaymentSummaryResponse:
    if payment_type == "membership_fee":
        preview = preview_membership_fee_generation(db=db, period=period)
        paid_count = sum(1 for row in preview.rows if row.status == "paid")
        partial_count = sum(1 for row in preview.rows if row.status == "partial")
        unpaid_count = sum(1 for row in preview.rows if row.status == "unpaid")
        need_check_count = sum(1 for row in preview.rows if row.status == "need_check")
        exempt_count = sum(1 for row in preview.rows if row.status == "exempt")
        return PaymentSummaryResponse(
            period=preview.current_term,
            payment_type=payment_type,
            required_amount=preview.new_member_fee,
            total_members=preview.summary.total_members,
            paid_count=paid_count,
            partial_count=partial_count,
            unpaid_count=unpaid_count,
            need_check_count=need_check_count,
            exempt_count=exempt_count,
            total_required_amount=preview.summary.total_required_amount,
            total_paid_amount=preview.summary.total_paid_amount,
        )

    # Get required_amount from app_settings (no fixed default)
    setting = db.execute(
        select(AppSetting).where(AppSetting.key == "membership_fee_amount")
    ).scalar_one_or_none()

    required_amount = 0
    if setting is not None and isinstance(setting.value, dict) and "amount" in setting.value:
        try:
            required_amount = int(setting.value["amount"])
        except (ValueError, TypeError):
            pass

    # Total members = ALL active members (not just those with records)
    active_members: list[Member] = db.execute(
        select(Member).where(Member.status == "active")
    ).scalars().all()
    total_members = len(active_members)
    active_ids = {m.id for m in active_members}

    # Payment records for this period/type
    records = db.execute(
        select(PaymentRecord).where(
            and_(
                PaymentRecord.period == period,
                PaymentRecord.payment_type == payment_type,
            )
        )
    ).scalars().all()

    # Only count records for active members
    active_records = [r for r in records if r.member_id in active_ids]

    paid_count = sum(1 for r in active_records if r.status == "paid")
    partial_count = sum(1 for r in active_records if r.status == "partial")
    need_check_count = sum(1 for r in active_records if r.status == "need_check")
    exempt_count = sum(1 for r in active_records if r.status == "exempt")
    total_paid_amount = sum(r.paid_amount for r in active_records)

    # Settled members: paid, partial, exempt are excluded from unpaid
    settled_ids = {
        r.member_id for r in active_records
        if r.status in ("paid", "partial", "exempt")
    }
    unpaid_count = total_members - len(settled_ids)
    total_required_amount = total_members * required_amount

    return PaymentSummaryResponse(
        period=period,
        payment_type=payment_type,
        required_amount=required_amount,
        total_members=total_members,
        paid_count=paid_count,
        partial_count=partial_count,
        unpaid_count=unpaid_count,
        need_check_count=need_check_count,
        exempt_count=exempt_count,
        total_required_amount=total_required_amount,
        total_paid_amount=total_paid_amount,
    )


@router.get("/unpaid", response_model=list[UnpaidPaymentItem])
def get_unpaid_members(
    period: str = Query(...),
    payment_type: str = Query(default="membership_fee"),
    db: Session = Depends(get_db),
) -> list[UnpaidPaymentItem]:
    if payment_type == "membership_fee":
        preview = preview_membership_fee_generation(db=db, period=period)
        return [
            UnpaidPaymentItem(
                member_id=row.member_id,
                name=row.member_name,
                student_id=row.student_id,
                department=row.department,
                required_amount=row.required_amount,
                paid_amount=row.paid_amount,
                status=row.status,
                payment_record_id=row.existing_record_id,
            )
            for row in preview.rows
            if row.status in ("unpaid", "need_check")
        ]

    # Get required_amount from app_settings (no fixed default)
    setting = db.execute(
        select(AppSetting).where(AppSetting.key == "membership_fee_amount")
    ).scalar_one_or_none()

    required_amount = 0
    if setting is not None and isinstance(setting.value, dict) and "amount" in setting.value:
        try:
            required_amount = int(setting.value["amount"])
        except (ValueError, TypeError):
            pass

    # Get active members
    active_members: list[Member] = db.execute(
        select(Member).where(Member.status == "active")
    ).scalars().all()

    # Get payment records for period + payment_type
    records = db.execute(
        select(PaymentRecord).where(
            and_(
                PaymentRecord.period == period,
                PaymentRecord.payment_type == payment_type,
            )
        )
    ).scalars().all()

    # Settled: paid / partial / exempt are excluded from unpaid list
    settled_ids: set[UUID] = {
        r.member_id for r in records if r.status in ("paid", "partial", "exempt")
    }

    # Build member_id → record map
    record_map = {r.member_id: r for r in records}

    unpaid_items: list[UnpaidPaymentItem] = []
    for member in active_members:
        if member.id in settled_ids:
            continue

        existing = record_map.get(member.id)
        paid_amount = existing.paid_amount if existing else 0
        status = existing.status if existing else "unpaid"
        record_id = existing.id if existing else None

        unpaid_items.append(
            UnpaidPaymentItem(
                member_id=member.id,
                name=member.name,
                student_id=member.student_id,
                department=member.department,
                required_amount=required_amount,
                paid_amount=paid_amount,
                status=status,
                payment_record_id=record_id,
            )
        )

    return unpaid_items


# ---------------------------------------------------------------------------
# Backward-compatibility alias endpoints
# (previously frontend called /api/payments/payment-matching/*)
# ---------------------------------------------------------------------------

@router.get("/payment-matching/summary", response_model=PaymentSummaryResponse, include_in_schema=False)
def get_payment_summary_alias(
    period: str = Query(...),
    payment_type: str = Query(default="membership_fee"),
    db: Session = Depends(get_db),
) -> PaymentSummaryResponse:
    return get_payment_summary(period=period, payment_type=payment_type, db=db)


@router.get("/payment-matching/unpaid", response_model=list[UnpaidPaymentItem], include_in_schema=False)
def get_unpaid_members_alias(
    period: str = Query(...),
    payment_type: str = Query(default="membership_fee"),
    db: Session = Depends(get_db),
) -> list[UnpaidPaymentItem]:
    return get_unpaid_members(period=period, payment_type=payment_type, db=db)
