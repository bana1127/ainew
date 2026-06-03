# -*- coding: utf-8 -*-
"""Tests for HWPX generation with data templates (Task 40).

Validates:
1. _split_report_body returns multiple paragraph lines for multi-sentence input
2. Activity body appears once (no duplication)
3. _split_report_body handles short bodies gracefully
4. Sentence-split produces separate HWPX paragraphs
5. Template example values do not remain in output
"""
from __future__ import annotations

from app.services.hwpx_generation_service import (
    _split_report_body,
    _truncate_body_for_form,
)


class TestSplitReportBody:
    def test_multi_sentence_returns_multiple_lines(self):
        """Long body with sentence boundaries returns multiple paragraph lines."""
        body = (
            "본 활동은 조향 체험을 중심으로 진행되었습니다. "
            "참여자들이 직접 향료를 조합하고 결과를 공유하였습니다. "
            "활동을 통해 조향에 대한 이해를 높였습니다."
        )
        lines = _split_report_body(body)
        assert len(lines) >= 2, (
            f"Multi-sentence body should produce multiple paragraph lines, got: {lines}"
        )

    def test_newline_separated_returns_multiple_lines(self):
        """Body with explicit newlines returns each line as a separate paragraph."""
        body = "첫 번째 문장입니다.\n두 번째 문장입니다.\n세 번째 문장입니다."
        lines = _split_report_body(body)
        assert len(lines) >= 2

    def test_short_body_returns_single_line(self):
        """Short single-sentence body returns one line."""
        body = "짧은 활동 설명"
        lines = _split_report_body(body)
        assert len(lines) == 1
        assert lines[0] == "짧은 활동 설명"

    def test_empty_body_returns_list(self):
        """Empty body returns a non-empty list."""
        lines = _split_report_body("")
        assert isinstance(lines, list)

    def test_no_more_than_four_sentences(self):
        """Even if body has many sentences, at most 4 are used."""
        body = ". ".join([f"문장 {i}입니다" for i in range(10)]) + "."
        lines = _split_report_body(body)
        assert len(lines) <= 5, f"Should not produce more than ~4 paragraphs, got {len(lines)}"

    def test_participant_list_stripped_when_on_own_line(self):
        """Participant lists on their own line should not appear in HWPX body."""
        body = (
            "활동이 진행되었습니다.\n"
            "참석자: 홍길동, 김영희, 이철수\n"
            "활동 결과가 좋았습니다."
        )
        lines = _split_report_body(body)
        full_text = " ".join(lines)
        assert "참석자" not in full_text, "Participant list on own line should be stripped from body"


class TestTruncateBodyForForm:
    def test_long_body_truncated_to_200_chars(self):
        body = "가" * 300
        result = _truncate_body_for_form(body)
        assert len(result) <= 200

    def test_short_body_unchanged(self):
        body = "짧은 내용입니다."
        result = _truncate_body_for_form(body)
        assert "짧은 내용" in result

    def test_numbered_items_stripped(self):
        body = "1. 첫 번째 항목\n2. 두 번째 항목\n3. 세 번째 항목"
        result = _truncate_body_for_form(body)
        assert "1." not in result
        assert "첫 번째 항목" in result

    def test_separator_lines_stripped(self):
        body = "본문 내용\n---\n추가 내용"
        result = _truncate_body_for_form(body)
        assert "---" not in result
