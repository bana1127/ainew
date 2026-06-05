"""Academic term service (학기 서비스).

회비 / 부원 납부 관리는 학기(term) 기준으로 관리합니다.
  1학기: 3월–8월  → "YYYY-1"
  2학기: 9월–2월(다음 해) → "YYYY-2"  (YYYY = 해당 학년도)

예:
  2026-03-01 → "2026-1"
  2026-08-31 → "2026-1"
  2026-09-01 → "2026-2"
  2027-02-28 → "2026-2"

주의: membership_fee PaymentRecord의 period는 항상 이 형식을 사용합니다.
      분기(quarter) 형식 "2026-Q2"로 바꾸면 절대 안 됩니다.
"""
from __future__ import annotations

from datetime import date
from typing import Tuple


def get_term_for_date(d: date) -> str:
    """Return the academic term string for a given date (e.g. '2026-1')."""
    month = d.month
    year = d.year
    if 3 <= month <= 8:
        return f"{year}-1"
    elif month >= 9:
        return f"{year}-2"
    else:  # January, February
        return f"{year - 1}-2"


def get_current_term() -> str:
    """Return the current academic term string."""
    return get_term_for_date(date.today())


def parse_term(term_str: str) -> Tuple[int, int]:
    """Parse '2026-1' -> (2026, 1)."""
    parts = term_str.split("-")
    if len(parts) != 2:
        raise ValueError(f"Invalid term format: '{term_str}'. Expected 'YYYY-N'")
    try:
        year = int(parts[0])
        term_num = int(parts[1])
    except ValueError:
        raise ValueError(f"Invalid term format: '{term_str}'")
    if term_num not in (1, 2):
        raise ValueError(f"Term number must be 1 or 2, got {term_num}")
    return year, term_num


def is_valid_term(term_str: str) -> bool:
    """Return True if term_str is a valid membership fee period."""
    try:
        parse_term(term_str)
        return True
    except ValueError:
        return False
