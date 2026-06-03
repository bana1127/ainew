from __future__ import annotations

from datetime import datetime as dt_type
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models import BankTransaction, UploadedFile
from app.models.payment import PaymentRecord
from app.routers.common import apply_updates, commit_or_400, get_or_404
from app.schemas import (
    BankStatementImportResponse,
    BankStatementPreviewResponse,
    BankTransactionCreate,
    BankTransactionRead,
    BankTransactionUpdate,
    ParsedBankTransactionRead,
)
from app.services.bank_statement_parser import parse_bank_statement

router = APIRouter()

ALLOWED_EXTENSIONS = {".xls", ".xlsx", ".csv"}


def _save_uploaded_file(file: UploadFile, db: Session) -> UploadedFile:
    settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    suffix = Path(file.filename or "").suffix.lower()
    stored_name = f"{uuid4()}{suffix}"
    stored_path = settings.UPLOAD_DIR / stored_name

    with stored_path.open("wb") as output:
        while chunk := file.file.read(1024 * 1024):
            output.write(chunk)

    record = UploadedFile(
        original_filename=file.filename or stored_name,
        stored_path=(Path("uploads") / stored_name).as_posix(),
        mime_type=file.content_type,
        file_type="bank_statement",
        related_entity_type="bank_transaction",
        related_entity_id=None,
    )
    db.add(record)
    commit_or_400(db, "Could not save uploaded file metadata")
    db.refresh(record)
    return record


@router.get("", response_model=list[BankTransactionRead])
def list_transactions(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    match_status: str | None = None,
    payment_type: str | None = None,
    matched_member_id: UUID | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    min_deposit: int | None = None,
    max_deposit: int | None = None,
    min_withdraw: int | None = None,
    max_withdraw: int | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
) -> list[BankTransaction]:
    stmt = select(BankTransaction)
    if match_status:
        stmt = stmt.where(BankTransaction.match_status == match_status)
    if payment_type:
        stmt = stmt.where(BankTransaction.payment_type == payment_type)
    if matched_member_id:
        stmt = stmt.where(BankTransaction.matched_member_id == matched_member_id)
    if start_date:
        try:
            stmt = stmt.where(
                BankTransaction.transaction_datetime >= dt_type.fromisoformat(start_date)
            )
        except ValueError:
            pass
    if end_date:
        try:
            stmt = stmt.where(
                BankTransaction.transaction_datetime <= dt_type.fromisoformat(end_date)
            )
        except ValueError:
            pass
    if min_deposit is not None:
        stmt = stmt.where(BankTransaction.deposit_amount >= min_deposit)
    if max_deposit is not None:
        stmt = stmt.where(BankTransaction.deposit_amount <= max_deposit)
    if min_withdraw is not None:
        stmt = stmt.where(BankTransaction.withdraw_amount >= min_withdraw)
    if max_withdraw is not None:
        stmt = stmt.where(BankTransaction.withdraw_amount <= max_withdraw)
    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(
            or_(
                BankTransaction.memo.ilike(pattern),
                BankTransaction.transaction_type.ilike(pattern),
                BankTransaction.branch.ilike(pattern),
            )
        )
    stmt = stmt.order_by(BankTransaction.transaction_datetime.desc())
    return list(db.scalars(stmt.offset(skip).limit(limit)))


@router.post("/parse-preview", response_model=BankStatementPreviewResponse)
def parse_preview(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> BankStatementPreviewResponse:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"지원하지 않는 파일 형식: {suffix}. 지원 형식: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    uploaded = _save_uploaded_file(file, db)
    full_path = settings.UPLOAD_DIR.parent / uploaded.stored_path
    result = parse_bank_statement(full_path)

    transactions = [
        ParsedBankTransactionRead(
            row_index=t.row_index,
            transaction_datetime=t.transaction_datetime,
            transaction_type=t.transaction_type,
            memo=t.memo,
            withdraw_amount=t.withdraw_amount,
            deposit_amount=t.deposit_amount,
            balance=t.balance,
            branch=t.branch,
            warnings=t.warnings,
        )
        for t in result.transactions
    ]

    return BankStatementPreviewResponse(
        file_id=uploaded.id,
        total_rows=result.total_rows,
        parsed_rows=result.parsed_rows,
        skipped_rows=result.skipped_rows,
        transactions=transactions,
        errors=result.errors,
        warnings=result.warnings,
    )


@router.post("/import", response_model=BankStatementImportResponse)
def import_transactions(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> BankStatementImportResponse:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"지원하지 않는 파일 형식: {suffix}. 지원 형식: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    uploaded = _save_uploaded_file(file, db)
    full_path = settings.UPLOAD_DIR.parent / uploaded.stored_path
    result = parse_bank_statement(full_path)

    inserted = 0
    duplicates = 0

    for t in result.transactions:
        if t.transaction_datetime is None:
            continue

        dup_stmt = select(BankTransaction).where(
            and_(
                BankTransaction.transaction_datetime == t.transaction_datetime,
                BankTransaction.memo == t.memo,
                BankTransaction.withdraw_amount == t.withdraw_amount,
                BankTransaction.deposit_amount == t.deposit_amount,
                BankTransaction.balance == t.balance,
            )
        )
        if db.scalars(dup_stmt).first() is not None:
            duplicates += 1
            continue

        row = BankTransaction(
            transaction_datetime=t.transaction_datetime,
            transaction_type=t.transaction_type,
            memo=t.memo,
            withdraw_amount=t.withdraw_amount,
            deposit_amount=t.deposit_amount,
            balance=t.balance,
            branch=t.branch,
            raw_json=t.raw_json,
            match_status="unmatched",
            # TODO(Task 6): Add member matching logic here
        )
        db.add(row)
        inserted += 1

    if inserted > 0:
        commit_or_400(db, "Could not save transactions")

    return BankStatementImportResponse(
        file_id=uploaded.id,
        total_rows=result.total_rows,
        parsed_rows=result.parsed_rows,
        inserted_rows=inserted,
        skipped_rows=result.skipped_rows,
        duplicate_rows=duplicates,
        errors=result.errors,
        warnings=result.warnings,
    )


@router.post("/{transaction_id}/unmatch")
def unmatch_transaction(
    transaction_id: UUID,
    db: Session = Depends(get_db),
) -> dict:
    """Cancel match for a bank transaction and restore linked payment record to unpaid."""
    transaction: BankTransaction = get_or_404(db, BankTransaction, transaction_id, "Transaction")

    # Find linked payment records (a transaction can link to multiple records)
    linked_records = list(db.scalars(
        select(PaymentRecord).where(PaymentRecord.transaction_id == transaction_id)
    ))

    for record in linked_records:
        record.transaction_id = None
        # Recalculate status
        if record.paid_amount == 0:
            record.status = "unpaid"
        elif record.paid_amount < record.required_amount:
            record.status = "partial"
        else:
            record.status = "paid"

    # Reset transaction
    transaction.match_status = "unmatched"
    transaction.matched_member_id = None

    commit_or_400(db, "Could not unmatch transaction")

    return {
        "ok": True,
        "transaction_id": str(transaction.id),
        "match_status": "unmatched",
        "unmatched_records": len(linked_records),
    }


# ── Task 21: Refund matching endpoints ────────────────────────────────────────

from pydantic import BaseModel as _BaseModel


class MatchRefundPayload(_BaseModel):
    payment_record_id: str
    refund_amount: int | None = None


@router.post("/{transaction_id}/match-refund")
def match_refund(
    transaction_id: UUID,
    payload: MatchRefundPayload,
    db: Session = Depends(get_db),
) -> dict:
    """Match a withdraw transaction as a refund for a payment record."""
    transaction = get_or_404(db, BankTransaction, transaction_id, "Transaction")

    if transaction.withdraw_amount == 0:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400,
            detail="출금 거래내역만 환불로 매칭할 수 있습니다.",
        )

    from uuid import UUID as _UUID
    from app.services.settlement_service import mark_refunded, create_adjustment_log

    record_id = _UUID(payload.payment_record_id)
    record = db.get(PaymentRecord, record_id)
    if not record:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="PaymentRecord not found")

    refund_amount = payload.refund_amount or transaction.withdraw_amount

    record = mark_refunded(
        db,
        record_id=record_id,
        refund_transaction_id=transaction_id,
        refund_amount=refund_amount,
        reason="출금 거래내역 환불 매칭",
    )

    transaction.match_status = "refund_matched"
    transaction.matched_member_id = record.member_id

    commit_or_400(db, "Could not match refund")
    db.refresh(record)

    return {
        "ok": True,
        "transaction_id": str(transaction_id),
        "payment_record_id": str(record_id),
        "refund_status": record.refund_status,
        "refund_amount": record.refund_amount,
        "transaction_match_status": transaction.match_status,
    }


@router.post("/{transaction_id}/unmatch-refund")
def unmatch_refund(
    transaction_id: UUID,
    db: Session = Depends(get_db),
) -> dict:
    """Cancel refund match for a transaction."""
    transaction = get_or_404(db, BankTransaction, transaction_id, "Transaction")

    from app.services.settlement_service import create_adjustment_log

    linked = list(db.scalars(
        select(PaymentRecord).where(
            PaymentRecord.refund_transaction_id == transaction_id
        )
    ))

    for record in linked:
        prev_refund = record.refund_status
        record.refund_transaction_id = None
        record.refund_status = "refund_pending" if prev_refund == "refunded" else "refund_required"
        record.refunded_at = None

        create_adjustment_log(
            db,
            payment_record_id=record.id,
            transaction_id=transaction_id,
            action="refund_cancelled",
            previous_status=prev_refund,
            new_status=record.refund_status,
            reason="환불 매칭 취소",
        )

    transaction.match_status = "unmatched"
    transaction.matched_member_id = None

    commit_or_400(db, "Could not unmatch refund")

    return {
        "ok": True,
        "transaction_id": str(transaction_id),
        "match_status": "unmatched",
        "unmatched_refunds": len(linked),
    }


@router.post("", response_model=BankTransactionRead)
def create_transaction(
    payload: BankTransactionCreate,
    db: Session = Depends(get_db),
) -> BankTransaction:
    transaction = BankTransaction(**payload.model_dump())
    db.add(transaction)
    commit_or_400(db, "Could not create transaction")
    db.refresh(transaction)
    return transaction


@router.get("/{transaction_id}", response_model=BankTransactionRead)
def get_transaction(
    transaction_id: UUID,
    db: Session = Depends(get_db),
) -> BankTransaction:
    return get_or_404(db, BankTransaction, transaction_id, "Transaction")


@router.patch("/{transaction_id}", response_model=BankTransactionRead)
def update_transaction(
    transaction_id: UUID,
    payload: BankTransactionUpdate,
    db: Session = Depends(get_db),
) -> BankTransaction:
    transaction = get_or_404(db, BankTransaction, transaction_id, "Transaction")
    apply_updates(transaction, payload)
    commit_or_400(db, "Could not update transaction")
    db.refresh(transaction)
    return transaction


@router.delete("/{transaction_id}", response_model=BankTransactionRead)
def delete_transaction(
    transaction_id: UUID,
    db: Session = Depends(get_db),
) -> BankTransaction:
    transaction = get_or_404(db, BankTransaction, transaction_id, "Transaction")
    db.delete(transaction)
    commit_or_400(db, "Could not delete transaction")
    return transaction
