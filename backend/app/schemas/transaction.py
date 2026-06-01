from datetime import datetime
from typing import Any
from uuid import UUID

from app.schemas.common import ORMModel


class BankTransactionBase(ORMModel):
    transaction_datetime: datetime | None = None
    transaction_type: str | None = None
    memo: str | None = None
    withdraw_amount: int = 0
    deposit_amount: int = 0
    balance: int | None = None
    branch: str | None = None
    raw_json: dict[str, Any] | None = None
    matched_member_id: UUID | None = None
    payment_type: str | None = None
    match_status: str = "unmatched"


class BankTransactionCreate(BankTransactionBase):
    pass


class BankTransactionUpdate(ORMModel):
    transaction_datetime: datetime | None = None
    transaction_type: str | None = None
    memo: str | None = None
    withdraw_amount: int | None = None
    deposit_amount: int | None = None
    balance: int | None = None
    branch: str | None = None
    raw_json: dict[str, Any] | None = None
    matched_member_id: UUID | None = None
    payment_type: str | None = None
    match_status: str | None = None


class BankTransactionRead(BankTransactionBase):
    id: UUID
    created_at: datetime
    updated_at: datetime


class ParsedBankTransactionRead(ORMModel):
    row_index: int
    transaction_datetime: datetime | None = None
    transaction_type: str | None = None
    memo: str | None = None
    withdraw_amount: int = 0
    deposit_amount: int = 0
    balance: int | None = None
    branch: str | None = None
    warnings: list[str] = []


class BankStatementPreviewResponse(ORMModel):
    file_id: UUID
    total_rows: int
    parsed_rows: int
    skipped_rows: int
    transactions: list[ParsedBankTransactionRead]
    errors: list[str]
    warnings: list[str]


class BankStatementImportResponse(ORMModel):
    file_id: UUID
    total_rows: int
    parsed_rows: int
    inserted_rows: int
    skipped_rows: int
    duplicate_rows: int
    errors: list[str]
    warnings: list[str]

