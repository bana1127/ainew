"""Unit tests for bank_statement_parser module."""
from datetime import datetime
from io import StringIO
from pathlib import Path

import pandas as pd
import pytest

from app.services.bank_statement_parser import (
    BankStatementParseResult,
    find_header_row,
    normalize_amount,
    normalize_datetime,
    parse_bank_statement,
    _is_summary,
)


class TestNormalizeAmount:
    def test_plain_number(self):
        assert normalize_amount("30000") == 30000

    def test_comma_separated(self):
        assert normalize_amount("30,000") == 30000

    def test_with_won_sign(self):
        assert normalize_amount("30,000원") == 30000

    def test_negative_parentheses(self):
        assert normalize_amount("(30,000)") == -30000

    def test_empty_string(self):
        assert normalize_amount("") == 0

    def test_dash(self):
        assert normalize_amount("-") == 0

    def test_zero(self):
        assert normalize_amount("0") == 0

    def test_none(self):
        assert normalize_amount(None) == 0

    def test_nan(self):
        import math
        assert normalize_amount(float("nan")) == 0


class TestNormalizeDatetime:
    def test_dot_format_with_time(self):
        result = normalize_datetime("2026.02.25 13:10:01")
        assert result == datetime(2026, 2, 25, 13, 10, 1)

    def test_dash_format_with_time(self):
        result = normalize_datetime("2026-02-25 13:10:01")
        assert result == datetime(2026, 2, 25, 13, 10, 1)

    def test_slash_format_without_seconds(self):
        result = normalize_datetime("2026/02/25 13:10")
        assert result == datetime(2026, 2, 25, 13, 10, 0)

    def test_dot_format_date_only(self):
        result = normalize_datetime("2026.02.25")
        assert result == datetime(2026, 2, 25, 0, 0, 0)

    def test_compact_format(self):
        result = normalize_datetime("20260225")
        assert result == datetime(2026, 2, 25, 0, 0, 0)

    def test_empty_string(self):
        assert normalize_datetime("") is None

    def test_dash(self):
        assert normalize_datetime("-") is None

    def test_unparseable(self):
        assert normalize_datetime("invalid-date") is None

    def test_datetime_passthrough(self):
        dt = datetime(2026, 1, 1)
        assert normalize_datetime(dt) == dt


class TestIsSummary:
    def test_sum_in_dt(self):
        assert _is_summary("합계", "") is True

    def test_sum_in_memo(self):
        assert _is_summary("", "합계") is True

    def test_total_in_dt(self):
        assert _is_summary("총계", "") is True

    def test_normal_row(self):
        assert _is_summary("2026.02.25 13:10:01", "메모아 홍길동") is False


class TestFindHeaderRow:
    def test_header_in_first_row(self):
        df = pd.DataFrame([["거래일시", "구분", "적요"], ["2026.02.25", "입금", "테스트"]])
        assert find_header_row(df) == 0

    def test_header_in_middle_row(self):
        df = pd.DataFrame([
            ["계좌번호", "12345"],
            ["잔액", "1000000"],
            ["거래일시", "구분", "적요", "출금액", "입금액"],
            ["2026.02.25", "입금", "홍길동", "0", "30000"],
        ])
        assert find_header_row(df) == 2

    def test_no_header(self):
        df = pd.DataFrame([["날짜", "금액"], ["2026.02.25", "30000"]])
        assert find_header_row(df) is None


class TestParseBankStatement:
    def _make_xlsx(self, tmp_path: Path) -> Path:
        """Create a minimal valid bank statement xlsx for testing."""
        rows = [
            ["거래내역조회"],
            ["계좌번호", "123-456-789"],
            ["거래일시", "구분", "적요", "출금액", "입금액", "잔액", "거래점"],
            ["2026.02.25 13:10:01", "입금", "메모아 홍길동", "0", "30,000", "500,000", "스마트뱅킹"],
            ["2026.02.26 09:00:00", "출금", "ATM출금", "50,000", "0", "450,000", "강남지점"],
            ["합계", "", "", "50,000", "30,000", "", ""],
        ]
        df = pd.DataFrame(rows)
        path = tmp_path / "test_statement.xlsx"
        df.to_excel(path, index=False, header=False, engine="openpyxl")
        return path

    def test_parse_xlsx(self, tmp_path):
        path = self._make_xlsx(tmp_path)
        result = parse_bank_statement(path)
        assert result.errors == []
        assert result.parsed_rows == 2
        assert result.skipped_rows >= 1  # 합계 row skipped
        t = result.transactions[0]
        assert t.deposit_amount == 30000
        assert t.withdraw_amount == 0
        assert t.balance == 500000
        assert t.memo == "메모아 홍길동"

    def test_missing_required_column(self, tmp_path):
        # No 거래일시 header => error
        df = pd.DataFrame([["날짜", "금액"], ["2026.02.25", "30000"]])
        path = tmp_path / "bad.xlsx"
        df.to_excel(path, index=False, header=False, engine="openpyxl")
        result = parse_bank_statement(path)
        assert len(result.errors) > 0

    def test_unsupported_extension(self, tmp_path):
        path = tmp_path / "file.pdf"
        path.write_bytes(b"dummy")
        result = parse_bank_statement(path)
        assert len(result.warnings) > 0 or len(result.errors) > 0
