"""Tests for operating quarter service (Task 43)."""
from __future__ import annotations

from datetime import date

import pytest

from app.services.quarter_service import (
    get_operating_quarter,
    get_quarter_date_range,
    parse_operating_quarter,
    quarter_date_range_from_str,
)


# ─── get_operating_quarter ───────────────────────────────────────────────────

def test_december_maps_to_next_year_q1() -> None:
    assert get_operating_quarter(date(2025, 12, 15)) == "2026-Q1"


def test_january_maps_to_q1() -> None:
    assert get_operating_quarter(date(2026, 1, 10)) == "2026-Q1"


def test_february_maps_to_q1() -> None:
    assert get_operating_quarter(date(2026, 2, 28)) == "2026-Q1"


def test_march_maps_to_q2() -> None:
    assert get_operating_quarter(date(2026, 3, 1)) == "2026-Q2"


def test_may_maps_to_q2() -> None:
    assert get_operating_quarter(date(2026, 5, 31)) == "2026-Q2"


def test_june_maps_to_q3() -> None:
    assert get_operating_quarter(date(2026, 6, 1)) == "2026-Q3"


def test_august_maps_to_q3() -> None:
    assert get_operating_quarter(date(2026, 8, 31)) == "2026-Q3"


def test_september_maps_to_q4() -> None:
    assert get_operating_quarter(date(2026, 9, 1)) == "2026-Q4"


def test_november_maps_to_q4() -> None:
    assert get_operating_quarter(date(2026, 11, 30)) == "2026-Q4"


# ─── get_quarter_date_range ───────────────────────────────────────────────────

def test_q1_range_starts_in_december_prior_year() -> None:
    start, end = get_quarter_date_range(2026, 1)
    assert start == date(2025, 12, 1)
    assert end == date(2026, 2, 28)


def test_q2_range() -> None:
    start, end = get_quarter_date_range(2026, 2)
    assert start == date(2026, 3, 1)
    assert end == date(2026, 5, 31)


def test_q3_range() -> None:
    start, end = get_quarter_date_range(2026, 3)
    assert start == date(2026, 6, 1)
    assert end == date(2026, 8, 31)


def test_q4_range() -> None:
    start, end = get_quarter_date_range(2026, 4)
    assert start == date(2026, 9, 1)
    assert end == date(2026, 11, 30)


def test_q1_leap_year_ends_feb_29() -> None:
    start, end = get_quarter_date_range(2028, 1)
    assert end == date(2028, 2, 29)


def test_invalid_quarter_raises() -> None:
    with pytest.raises(ValueError):
        get_quarter_date_range(2026, 5)


# ─── parse_operating_quarter ──────────────────────────────────────────────────

def test_parse_quarter_string() -> None:
    assert parse_operating_quarter("2026-Q2") == (2026, 2)


def test_parse_quarter_string_case_insensitive() -> None:
    assert parse_operating_quarter("2026-q3") == (2026, 3)


def test_parse_invalid_quarter_format_raises() -> None:
    with pytest.raises(ValueError):
        parse_operating_quarter("2026-2")  # not Q format


def test_parse_invalid_quarter_number_raises() -> None:
    with pytest.raises(ValueError):
        parse_operating_quarter("2026-Q5")


# ─── quarter_date_range_from_str ──────────────────────────────────────────────

def test_quarter_date_range_from_str_q1() -> None:
    start, end = quarter_date_range_from_str("2026-Q1")
    assert start == date(2025, 12, 1)
    assert end == date(2026, 2, 28)


def test_quarter_date_range_from_str_q2() -> None:
    start, end = quarter_date_range_from_str("2026-Q2")
    assert start == date(2026, 3, 1)
    assert end == date(2026, 5, 31)
