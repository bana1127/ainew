"""Budget export service: quarter-based ZIP and CSV export."""
from __future__ import annotations

import csv
import io
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.services.quarter_service import quarter_date_range_from_str


def get_quarter_transactions(db: Session, operating_quarter: str) -> list[Any]:
    from app.models.transaction import BankTransaction

    q_start, q_end = quarter_date_range_from_str(operating_quarter)
    stmt = (
        select(BankTransaction)
        .where(
            and_(
                BankTransaction.transaction_datetime
                >= datetime.combine(q_start, datetime.min.time()),
                BankTransaction.transaction_datetime
                <= datetime.combine(q_end, datetime.max.time()),
            )
        )
        .order_by(BankTransaction.transaction_datetime)
    )
    return list(db.scalars(stmt))


def get_quarter_receipts(db: Session, operating_quarter: str) -> list[Any]:
    from app.models.receipt import Receipt

    q_start, q_end = quarter_date_range_from_str(operating_quarter)
    stmt = (
        select(Receipt)
        .where(
            and_(
                Receipt.receipt_date >= q_start,
                Receipt.receipt_date <= q_end,
            )
        )
        .order_by(Receipt.receipt_date)
    )
    return list(db.scalars(stmt))


def build_transaction_csv(transactions: list[Any]) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "거래일시", "거래구분", "적요", "출금(원)", "입금(원)", "잔액",
        "납부유형", "매칭상태", "예산제외여부", "제외사유",
    ])
    for tx in transactions:
        writer.writerow([
            tx.transaction_datetime.strftime("%Y-%m-%d %H:%M") if tx.transaction_datetime else "",
            tx.transaction_type or "",
            tx.memo or "",
            tx.withdraw_amount or 0,
            tx.deposit_amount or 0,
            tx.balance or "",
            tx.payment_type or "",
            tx.match_status or "",
            "Y" if (tx.exclude_from_budget or tx.exclude_from_income or tx.exclude_from_expense) else "N",
            tx.exclude_reason or "",
        ])
    return output.getvalue()


def build_receipt_csv(receipts: list[Any]) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "발급일", "문서유형", "제목", "상호/업체", "금액(원)", "결제방법",
        "증빙상태", "확인필요여부",
    ])
    for r in receipts:
        writer.writerow([
            str(r.receipt_date) if r.receipt_date else "",
            r.document_type or "unknown",
            r.title or r.store_name or "",
            r.store_name or "",
            r.amount or 0,
            r.payment_method or "",
            r.evidence_status or "",
            "Y" if r.need_check else "N",
        ])
    return output.getvalue()


def build_quarter_zip(
    db: Session,
    operating_quarter: str,
    upload_dir: Path,
) -> bytes:
    """Build a ZIP archive for the given operating quarter.

    Contents:
    - transactions.csv  거래내역
    - receipts.csv      증빙 목록
    - evidence/         실제 증빙 파일 (uploaded_files)
    """
    transactions = get_quarter_transactions(db, operating_quarter)
    receipts = get_quarter_receipts(db, operating_quarter)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # 거래내역 CSV
        zf.writestr(
            f"{operating_quarter}_transactions.csv",
            build_transaction_csv(transactions).encode("utf-8-sig").decode("latin-1", errors="replace"),
        )
        # 증빙 목록 CSV
        zf.writestr(
            f"{operating_quarter}_receipts.csv",
            build_receipt_csv(receipts).encode("utf-8-sig").decode("latin-1", errors="replace"),
        )
        # 실제 증빙 파일
        for receipt in receipts:
            if receipt.file_id:
                from app.models.file import UploadedFile
                uf = db.get(UploadedFile, receipt.file_id)
                if uf and uf.stored_path:
                    file_path = upload_dir.parent / uf.stored_path
                    if file_path.exists():
                        ext = Path(uf.original_filename or uf.stored_path).suffix
                        doc_type = receipt.document_type or "unknown"
                        label = receipt.title or receipt.store_name or str(receipt.id)[:8]
                        arc_name = f"evidence/{doc_type}/{label}{ext}"
                        zf.write(file_path, arc_name)

    return buf.getvalue()
