"""Operating quarter service.

운영 분기 기준:
  1분기 (Q1): 12월(전년도), 1월, 2월
  2분기 (Q2): 3월, 4월, 5월
  3분기 (Q3): 6월, 7월, 8월
  4분기 (Q4): 9월, 10월, 11월

예: 2025-12-15 → 2026-Q1, 2026-03-01 → 2026-Q2
"""
from __future__ import annotations

import calendar
from datetime import date
from typing import Tuple


def get_operating_quarter(d: date) -> str:
    """Return operating quarter label for a given date (e.g. '2026-Q1')."""
    month = d.month
    year = d.year
    if month == 12:
        return f"{year + 1}-Q1"
    elif month in (1, 2):
        return f"{year}-Q1"
    elif month in (3, 4, 5):
        return f"{year}-Q2"
    elif month in (6, 7, 8):
        return f"{year}-Q3"
    else:  # 9, 10, 11
        return f"{year}-Q4"


def get_quarter_date_range(year: int, quarter: int) -> Tuple[date, date]:
    """Return (start_date, end_date) inclusive for a given operating quarter.

    Q1: Dec 1 (year-1) – Feb last day (year)
    Q2: Mar 1 – May 31
    Q3: Jun 1 – Aug 31
    Q4: Sep 1 – Nov 30
    """
    if quarter == 1:
        start = date(year - 1, 12, 1)
        feb_days = calendar.monthrange(year, 2)[1]
        end = date(year, 2, feb_days)
    elif quarter == 2:
        start = date(year, 3, 1)
        end = date(year, 5, 31)
    elif quarter == 3:
        start = date(year, 6, 1)
        end = date(year, 8, 31)
    elif quarter == 4:
        start = date(year, 9, 1)
        end = date(year, 11, 30)
    else:
        raise ValueError(f"quarter must be 1–4, got {quarter}")
    return start, end


def parse_operating_quarter(quarter_str: str) -> Tuple[int, int]:
    """Parse '2026-Q1' -> (2026, 1)."""
    parts = quarter_str.upper().split("-Q")
    if len(parts) != 2:
        raise ValueError(f"Invalid quarter format: '{quarter_str}'. Expected 'YYYY-Qn'")
    try:
        year = int(parts[0])
        quarter = int(parts[1])
    except ValueError:
        raise ValueError(f"Invalid quarter format: '{quarter_str}'")
    if quarter not in (1, 2, 3, 4):
        raise ValueError(f"Quarter must be 1–4, got {quarter}")
    return year, quarter


def get_current_operating_quarter() -> str:
    """Return the operating quarter label for today."""
    return get_operating_quarter(date.today())


def quarter_date_range_from_str(quarter_str: str) -> Tuple[date, date]:
    """Convenience: parse '2026-Q2' and return (start_date, end_date)."""
    year, q = parse_operating_quarter(quarter_str)
    return get_quarter_date_range(year, q)
