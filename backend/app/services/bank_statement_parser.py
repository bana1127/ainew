from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import pandas as pd


COLUMN_ALIASES: dict[str, list[str]] = {
    "transaction_datetime": ["거래일시", "거래일자", "일시", "거래일"],
    "transaction_type": ["구분", "거래구분", "입출금"],
    "memo": ["적요", "내용", "거래내용", "입금자명", "보낸분/받는분"],
    "withdraw_amount": ["출금액", "출금", "지급액", "지출액"],
    "deposit_amount": ["입금액", "입금", "입금액(원)"],
    "balance": ["잔액", "거래후잔액"],
    "branch": ["거래점", "취급점", "지점"],
}

SUMMARY_KEYWORDS = ["합계", "합 계", "총계", "소계"]


@dataclass
class ParsedBankTransaction:
    transaction_datetime: datetime | None
    transaction_type: str | None
    memo: str | None
    withdraw_amount: int
    deposit_amount: int
    balance: int | None
    branch: str | None
    raw_json: dict
    row_index: int
    warnings: list[str] = field(default_factory=list)


@dataclass
class BankStatementParseResult:
    total_rows: int
    parsed_rows: int
    skipped_rows: int
    transactions: list[ParsedBankTransaction]
    errors: list[str]
    warnings: list[str]


def _str_val(v: object) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and v != v:
        return ""
    return str(v).strip()


def normalize_amount(value: object) -> int:
    """Convert amount cell value to int. "(30,000)" -> -30000, "30,000원" -> 30000, "" -> 0."""
    s = _str_val(value)
    if not s or s in ("-", "—", "N/A", "n/a", "nan", "None"):
        return 0
    negative = s.startswith("(") and s.endswith(")")
    s = s.strip("()")
    s = re.sub(r"[,원\s]", "", s)
    if not s or s in ("-", "—"):
        return 0
    try:
        result = int(float(s))
        return -result if negative else result
    except (ValueError, TypeError):
        return 0


def normalize_datetime(value: object) -> datetime | None:
    """Parse Korean bank date strings to datetime."""
    if isinstance(value, datetime):
        return value
    s = _str_val(value)
    if not s or s in ("-", "—", "nan", "None"):
        return None
    formats = [
        "%Y.%m.%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
        "%Y.%m.%d %H:%M",
        "%Y-%m-%d %H:%M",
        "%Y/%m/%d %H:%M",
        "%Y.%m.%d",
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%Y%m%d",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def _is_summary(dt_str: str, memo_str: str) -> bool:
    for kw in SUMMARY_KEYWORDS:
        if kw in dt_str or kw in memo_str:
            return True
    return False


def find_header_row(df: pd.DataFrame) -> int | None:
    """Scan all rows for a cell containing 거래일시. Return its positional index."""
    for i in range(len(df)):
        row = df.iloc[i]
        for cell in row:
            if isinstance(cell, str) and "거래일시" in cell.strip():
                return i
    return None


def _load_dataframe(file_path: Path, warnings: list[str]) -> pd.DataFrame | None:
    suffix = file_path.suffix.lower()

    if suffix == ".xlsx":
        try:
            return pd.read_excel(file_path, header=None, engine="openpyxl", dtype=str)
        except Exception as exc:
            warnings.append(f"xlsx 읽기 실패: {exc}")
            return None

    if suffix == ".xls":
        try:
            return pd.read_excel(file_path, header=None, engine="xlrd", dtype=str)
        except Exception as exc:
            warnings.append(f"xlrd 파싱 실패, HTML fallback 시도: {exc}")
            try:
                tables = pd.read_html(str(file_path), header=None)
                if tables:
                    return tables[0].astype(str)
                warnings.append("HTML fallback: 테이블 없음")
            except Exception as exc2:
                warnings.append(f"HTML fallback 실패: {exc2}")
            return None

    if suffix == ".csv":
        for enc in ("utf-8-sig", "cp949", "utf-8"):
            try:
                return pd.read_csv(file_path, header=None, dtype=str, encoding=enc)
            except (UnicodeDecodeError, Exception):
                continue
        warnings.append("CSV 인코딩 감지 실패 (utf-8-sig, cp949, utf-8 모두 실패)")
        return None

    warnings.append(f"지원하지 않는 파일 형식: {suffix}")
    return None


def parse_bank_statement(file_path: Path) -> BankStatementParseResult:
    """Parse a bank statement file into structured transaction records."""
    errors: list[str] = []
    warnings: list[str] = []

    raw_df = _load_dataframe(file_path, warnings)
    if raw_df is None:
        errors.append("파일을 읽을 수 없습니다")
        return BankStatementParseResult(0, 0, 0, [], errors, warnings)

    header_idx = find_header_row(raw_df)
    if header_idx is None:
        errors.append("거래일시 헤더 행을 찾을 수 없습니다")
        return BankStatementParseResult(0, 0, 0, [], errors, warnings)

    header_values = [_str_val(v) for v in raw_df.iloc[header_idx].tolist()]
    data_df = raw_df.iloc[header_idx + 1 :].copy()
    data_df.columns = pd.Index(header_values)
    data_df = data_df.loc[:, data_df.columns.str.len() > 0]

    col_map: dict[str, str] = {}
    for std_name, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in data_df.columns:
                col_map[std_name] = alias
                break

    required = ["transaction_datetime", "withdraw_amount", "deposit_amount"]
    missing = [r for r in required if r not in col_map]
    if missing:
        errors.append(f"필수 컬럼 없음: {missing}")
        return BankStatementParseResult(0, 0, 0, [], errors, warnings)

    transactions: list[ParsedBankTransaction] = []
    skipped = 0
    total_rows = len(data_df)

    dt_col = col_map["transaction_datetime"]
    memo_col = col_map.get("memo", "")
    withdraw_col = col_map["withdraw_amount"]
    deposit_col = col_map["deposit_amount"]
    balance_col = col_map.get("balance", "")
    type_col = col_map.get("transaction_type", "")
    branch_col = col_map.get("branch", "")

    for pos, (_, row) in enumerate(data_df.iterrows()):
        dt_str = _str_val(row.get(dt_col, ""))
        memo_str = _str_val(row.get(memo_col, "")) if memo_col else ""

        if not dt_str and not memo_str:
            skipped += 1
            continue

        if _is_summary(dt_str, memo_str):
            skipped += 1
            continue

        row_warnings: list[str] = []
        dt = normalize_datetime(dt_str)
        if dt is None:
            if dt_str:
                row_warnings.append(f"날짜 파싱 실패: {dt_str!r}")
            skipped += 1
            warnings.extend(row_warnings)
            continue

        withdraw = normalize_amount(row.get(withdraw_col, ""))
        deposit = normalize_amount(row.get(deposit_col, ""))

        balance_str = _str_val(row.get(balance_col, "")) if balance_col else ""
        balance_val: int | None = (
            normalize_amount(balance_str)
            if balance_str and balance_str not in ("-", "—")
            else None
        )

        transaction_type = _str_val(row.get(type_col, "")) if type_col else ""
        branch = _str_val(row.get(branch_col, "")) if branch_col else ""

        for sentinel in ("None", "nan", "NaN", ""):
            if transaction_type == sentinel:
                transaction_type = ""
                break
        for sentinel in ("None", "nan", "NaN", ""):
            if branch == sentinel:
                branch = ""
                break
        for sentinel in ("None", "nan", "NaN"):
            if memo_str == sentinel:
                memo_str = ""
                break

        raw_json: dict = {str(k): (_str_val(v) or None) for k, v in row.items()}

        transactions.append(
            ParsedBankTransaction(
                transaction_datetime=dt,
                transaction_type=transaction_type or None,
                memo=memo_str or None,
                withdraw_amount=withdraw,
                deposit_amount=deposit,
                balance=balance_val,
                branch=branch or None,
                raw_json=raw_json,
                row_index=header_idx + 1 + pos,
                warnings=row_warnings,
            )
        )

    return BankStatementParseResult(
        total_rows=total_rows,
        parsed_rows=len(transactions),
        skipped_rows=skipped,
        transactions=transactions,
        errors=errors,
        warnings=warnings,
    )
