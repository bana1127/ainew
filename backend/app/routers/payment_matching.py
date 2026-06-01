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
    )
    return _result_to_schema(result)


@router.patch("/transactions/{transaction_id}/confirm", response_model=PaymentRecordRead)
def confirm_transaction(
    transaction_id: UUID,
    payload: PaymentConfirmPayload,
    db: Session = Depends(get_db),
) -> PaymentRecordRead:
    transaction: BankTransaction = get_or_404(db, BankTransaction, transaction_id, "BankTransaction")
    member: Member = get_or_404(db, Member, payload.member_id, "Member")

    # Update bank transaction
    transaction.matched_member_id = member.id
    transaction.payment_type = payload.payment_type
    transaction.match_status = "matched"

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
    # Get required_amount from app_settings
    setting = db.execute(
        select(AppSetting).where(AppSetting.key == "membership_fee_amount")
    ).scalar_one_or_none()

    required_amount = 30000
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
    # Get required_amount from app_settings
    setting = db.execute(
        select(AppSetting).where(AppSetting.key == "membership_fee_amount")
    ).scalar_one_or_none()

    required_amount = 30000
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
