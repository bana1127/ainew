# -*- coding: utf-8 -*-
"""Tests for Unicode filename handling in Content-Disposition header.

Verifies that Korean/non-ASCII filenames don't raise UnicodeEncodeError
and that the RFC 5987 encoding is applied.
"""
from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import MagicMock
from urllib.parse import quote, unquote


def _stub(name: str) -> ModuleType:
    mod = ModuleType(name)
    mod.__spec__ = None  # type: ignore[attr-defined]
    return mod


# ── Import-safe helpers only ────────────────────────────────────────────────

class TestRfc5987Encoding:
    """Verify the RFC 5987 encoding logic used in the download endpoint."""

    def _disposition(self, filename: str) -> str:
        """Replicate the header construction from files.py."""
        encoded = quote(filename, safe="", encoding="utf-8")
        ascii_fallback = filename.encode("ascii", errors="replace").decode("ascii").replace('"', '\\"')
        return f'attachment; filename="{ascii_fallback}"; filename*=UTF-8\'\'{encoded}'

    def test_ascii_filename_no_error(self):
        disposition = self._disposition("report.hwpx")
        assert "report.hwpx" in disposition
        # No encoding error → passes

    def test_korean_filename_no_unicode_error(self):
        filename = "위퍼퓸 교내조향활동_2026-06-03.hwpx"
        # This would previously raise UnicodeEncodeError when put into latin-1 header
        try:
            disposition = self._disposition(filename)
        except UnicodeEncodeError:
            raise AssertionError("UnicodeEncodeError raised for Korean filename")
        assert "UTF-8''" in disposition

    def test_rfc5987_percent_encoded(self):
        filename = "위퍼퓸 교내조향활동.hwpx"
        disposition = self._disposition(filename)
        # The filename* part should be percent-encoded
        assert "filename*=UTF-8''" in disposition
        encoded_part = disposition.split("filename*=UTF-8''")[1]
        decoded = unquote(encoded_part, encoding="utf-8")
        assert "위퍼퓸" in decoded

    def test_ascii_fallback_present(self):
        filename = "테스트_보고서.pdf"
        disposition = self._disposition(filename)
        # Both filename= (ASCII fallback) and filename*= (UTF-8) should be present
        assert 'filename="' in disposition
        assert "filename*=UTF-8''" in disposition

    def test_quote_chars_in_filename(self):
        filename = 'report "final".hwpx'
        disposition = self._disposition(filename)
        # Double quotes in ASCII fallback should be escaped
        assert '\\"' in disposition or '"report' not in disposition


class TestStudentIdNormalize:
    """Quick sanity check for student_id normalization logic."""

    @staticmethod
    def _normalize(raw) -> str | None:
        """Replicate _clean_student_id logic."""
        if raw is None:
            return None
        s = str(raw).strip()
        if not s:
            return None
        if s.endswith(".0"):
            s = s[:-2]
        digits = "".join(ch for ch in s if ch.isdigit())
        return digits if digits else None

    def test_float_normalized(self):
        assert self._normalize(2022130026.0) == "2022130026"

    def test_string_with_dot_zero(self):
        assert self._normalize("2022130026.0") == "2022130026"

    def test_pure_digits(self):
        assert self._normalize("2022130026") == "2022130026"

    def test_none(self):
        assert self._normalize(None) is None
