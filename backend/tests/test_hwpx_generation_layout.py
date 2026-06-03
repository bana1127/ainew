# -*- coding: utf-8 -*-
"""Layout tests for hwpx_generation_service (Task 24 layout hotfix 2).

Verifies:
  1. Multi-line report_body → each line in a separate paragraph
  2. Participant roster → NOT joined with '|' on one line
  3. Each participant name/student_id in extracted text
  4. '|' separator pattern absent from extracted text
  5. Activity content not duplicated
  6. TABLE CELL NEIGHBOR replacement (HWPX form structure)
  7. TABLE ROW CLONE for participant roster (Method B)
  8. _find_enclosing_table_cell / _find_enclosing_table_row unit tests
"""
from __future__ import annotations

import io
import re
import zipfile
from pathlib import Path

import pytest

from app.services.hwpx_generation_service import (
    HwpxContext,
    _clone_paragraph_with_text,
    _find_enclosing_paragraph,
    _find_enclosing_table_cell,
    _find_enclosing_table_row,
    _find_next_element,
    _get_paragraphs_in_range,
    _replace_paragraph_after_heading,
    _replace_participant_roster,
    _TC_OPEN_RE,
    _TEXT_EL_RE,
    extract_hwpx_text,
    generate_hwpx,
)


# ── Test fixtures ─────────────────────────────────────────────────────────────

def _make_hwpx(section_xml: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as zf:
        zf.writestr("META-INF/container.xml", "<container/>")
        zf.writestr("Contents/section0.xml", section_xml.encode("utf-8"))
    return buf.getvalue()


def _write_hwpx(path: Path, section_xml: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_make_hwpx(section_xml))


# Template with realistic HWPX-style paragraph structure using hp: namespace
LEGACY_TEMPLATE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<hp:sec xmlns:hp="http://www.hancom.co.kr/hwpml/2011">
<hp:p><hp:run><hp:t>00월 [ Oui Parfum ] 동아리 활동 내역서</hp:t></hp:run></hp:p>
<hp:p><hp:run><hp:t>활동 장소</hp:t></hp:run></hp:p>
<hp:p><hp:run><hp:t>종합관 앞</hp:t></hp:run></hp:p>
<hp:p><hp:run><hp:t>활동 일시</hp:t></hp:run></hp:p>
<hp:p><hp:run><hp:t>2025.00.00</hp:t></hp:run></hp:p>
<hp:p><hp:run><hp:t>활동 분류</hp:t></hp:run></hp:p>
<hp:p><hp:run><hp:t>제89조 7항 교내 활동 참여</hp:t></hp:run></hp:p>
<hp:p><hp:run><hp:t>활동 내용</hp:t></hp:run></hp:p>
<hp:p><hp:run><hp:t>동아리 홍보전에 참여하여 신입생과 재학생들에게 동아리 가입을 도모하는 활동을 진행함</hp:t></hp:run></hp:p>
<hp:p><hp:run><hp:t>이하 생략</hp:t></hp:run></hp:p>
<hp:p><hp:run><hp:t>참여인원 총 00명</hp:t></hp:run></hp:p>
</hp:sec>"""

PARTICIPANTS = [
    {"name": "이주현", "department": "컴퓨터공학부", "student_id": "2022130026"},
    {"name": "심사무엘", "department": "기계공학부", "student_id": "2022200032"},
    {"name": "박우준", "department": "전자공학부", "student_id": "2023312035"},
]

MULTILINE_BODY = (
    "1. 활동명: 위퍼퓸 교내조향활동\n"
    "2. 활동 일시: 2026년 6월 3일\n"
    "3. 활동 장소: A401호\n"
    "4. 참석자: 이주현, 심사무엘, 박우준\n"
    "5. 활동 목적: 조향 체험을 통한 동아리 활동 활성화"
)


# ── Unit tests: _find_enclosing_paragraph ────────────────────────────────────

class TestFindEnclosingParagraph:
    def test_finds_hp_p(self):
        xml = "<hp:p><hp:t>hello world</hp:t></hp:p>"
        m = list(_TEXT_EL_RE.finditer(xml))[0]
        result = _find_enclosing_paragraph(xml, m.start())
        assert result is not None
        start, end, tag = result
        assert tag == "hp:p"
        assert xml[start:end] == xml

    def test_finds_plain_p(self):
        xml = "<p><t>content</t></p>"
        m = list(_TEXT_EL_RE.finditer(xml))[0]
        result = _find_enclosing_paragraph(xml, m.start())
        assert result is not None
        _, _, tag = result
        assert tag == "p"

    def test_nested_picks_innermost(self):
        xml = "<sec><hp:p><hp:t>inner text</hp:t></hp:p></sec>"
        m = list(_TEXT_EL_RE.finditer(xml))[0]
        result = _find_enclosing_paragraph(xml, m.start())
        assert result is not None
        start, end, tag = result
        assert tag == "hp:p"
        # Should point to the <hp:p>…</hp:p> block, not the outer <sec>
        assert xml[start:end] == "<hp:p><hp:t>inner text</hp:t></hp:p>"

    def test_no_paragraph_returns_none(self):
        xml = "<t>standalone text</t>"
        m = list(_TEXT_EL_RE.finditer(xml))[0]
        result = _find_enclosing_paragraph(xml, m.start())
        assert result is None


# ── Unit tests: _clone_paragraph_with_text ───────────────────────────────────

class TestCloneParagraphWithText:
    def test_replaces_text(self):
        para = "<hp:p><hp:run><hp:t>original text</hp:t></hp:run></hp:p>"
        cloned = _clone_paragraph_with_text(para, "new text")
        assert "new text" in cloned
        assert "original text" not in cloned

    def test_preserves_structure(self):
        para = "<hp:p><hp:run><hp:rPr><hp:b/></hp:rPr><hp:t>bold text</hp:t></hp:run></hp:p>"
        cloned = _clone_paragraph_with_text(para, "other")
        assert "<hp:rPr>" in cloned
        assert "<hp:b/>" in cloned
        assert "other" in cloned

    def test_multi_text_element_first_gets_text_rest_empty(self):
        para = "<hp:p><hp:t>first</hp:t><hp:t>second</hp:t></hp:p>"
        cloned = _clone_paragraph_with_text(para, "replaced")
        assert "replaced" in cloned
        assert "first" not in cloned
        assert "second" not in cloned


# ── Unit tests: _replace_paragraph_after_heading ─────────────────────────────

class TestReplaceParagraphAfterHeading:
    def test_single_line_replacement(self):
        xml = (
            "<hp:sec>"
            "<hp:p><hp:t>활동 장소</hp:t></hp:p>"
            "<hp:p><hp:t>종합관 앞</hp:t></hp:p>"
            "</hp:sec>"
        )
        new_xml, count, old = _replace_paragraph_after_heading(xml, "활동 장소", ["A401호"])
        assert "A401호" in new_xml
        assert "종합관 앞" not in new_xml
        assert old == "종합관 앞"
        assert count == 1

    def test_multiline_creates_multiple_paragraphs(self):
        xml = (
            "<hp:sec>"
            "<hp:p><hp:t>활동 내용</hp:t></hp:p>"
            "<hp:p><hp:t>예시 활동 내용입니다</hp:t></hp:p>"
            "</hp:sec>"
        )
        lines = ["1. 첫번째 항목", "2. 두번째 항목", "3. 세번째 항목"]
        new_xml, count, old = _replace_paragraph_after_heading(xml, "활동 내용", lines)

        assert count == 3
        for line in lines:
            assert line in new_xml
        assert "예시 활동 내용입니다" not in new_xml
        # Three separate paragraphs should exist
        assert new_xml.count("<hp:p>") >= 2  # heading + at least 2 content paras

    def test_heading_not_found_returns_unchanged(self):
        xml = "<hp:p><hp:t>무관한 내용</hp:t></hp:p>"
        new_xml, count, old = _replace_paragraph_after_heading(xml, "없는 헤딩", ["value"])
        assert new_xml == xml
        assert count == 0


# ── Unit tests: _replace_participant_roster ───────────────────────────────────

class TestReplaceParticipantRosterLayout:
    def test_no_pipe_separator(self):
        """Participants must NOT appear as 'name | name2 | ...' on a single line."""
        xml = "<hp:p><hp:t>이하 생략</hp:t></hp:p>"
        new_xml, count = _replace_participant_roster(xml, PARTICIPANTS)

        # Pipe-joined pattern must not exist
        extracted = re.sub(r'<[^>]+>', '', new_xml)
        assert " | " not in extracted or "이주현" not in extracted.split(" | ")[0], (
            "Participants should not be '|'-joined on a single line"
        )
        # Check all names are present
        assert "이주현" in new_xml
        assert "심사무엘" in new_xml
        assert "박우준" in new_xml

    def test_student_ids_present(self):
        xml = "<hp:p><hp:t>이하 생략</hp:t></hp:p>"
        new_xml, _ = _replace_participant_roster(xml, PARTICIPANTS)
        assert "2022130026" in new_xml
        assert "2022200032" in new_xml
        assert "2023312035" in new_xml

    def test_creates_multiple_paragraphs(self):
        """With 3 participants, expect at least 3 <hp:p> elements."""
        xml = "<hp:p><hp:t>이하 생략</hp:t></hp:p>"
        new_xml, count = _replace_participant_roster(xml, PARTICIPANTS)
        p_count = new_xml.count("<hp:p>")
        assert p_count >= 3, f"Expected ≥3 paragraphs, got {p_count}"
        assert count == 3

    def test_sorted_by_student_id(self):
        xml = "<hp:p><hp:t>이하 생략</hp:t></hp:p>"
        new_xml, _ = _replace_participant_roster(xml, PARTICIPANTS)
        # 2022130026 (이주현) < 2022200032 (심사무엘) < 2023312035 (박우준)
        pos_a = new_xml.find("2022130026")
        pos_b = new_xml.find("2022200032")
        pos_c = new_xml.find("2023312035")
        assert pos_a < pos_b < pos_c


# ── Integration tests: full generate_hwpx pipeline ───────────────────────────

class TestLayoutEndToEnd:
    def _make_ctx(self, **kw) -> HwpxContext:
        defaults = dict(
            activity_title="위퍼퓸 교내조향활동",
            activity_month="06",
            activity_date="2026.06.03",
            activity_location="A401호",
            activity_category="교내 활동 참여",
            report_body=MULTILINE_BODY,
            participant_count=len(PARTICIPANTS),
            participant_list=PARTICIPANTS,
            club_name="Oui Parfum",
        )
        defaults.update(kw)
        return HwpxContext(**defaults)

    # Test 1: Multi-line report_body → preserved as multiple lines
    def test_multiline_body_preserved(self, tmp_path):
        tpl = tmp_path / "t.hwpx"
        out = tmp_path / "o.hwpx"
        _write_hwpx(tpl, LEGACY_TEMPLATE_XML)

        ctx = self._make_ctx()
        generate_hwpx(tpl, out, ctx, mode="legacy_form")

        text = extract_hwpx_text(out)

        for line in MULTILINE_BODY.split("\n"):
            stripped = line.strip()
            if stripped:
                assert stripped in text, f"Line not found in output: {stripped!r}"

    # Test 2 & 4: Participants not joined with '|' on one line
    def test_participants_not_pipe_joined(self, tmp_path):
        tpl = tmp_path / "t.hwpx"
        out = tmp_path / "o.hwpx"
        _write_hwpx(tpl, LEGACY_TEMPLATE_XML)

        ctx = self._make_ctx()
        generate_hwpx(tpl, out, ctx, mode="legacy_form")

        text = extract_hwpx_text(out)

        # Must NOT contain the old pipe-join pattern
        assert "이주현  /  컴퓨터공학부  /  2022130026  |  심사무엘" not in text, (
            "Participants should not be '|'-joined in a single line"
        )

    # Test 3: Each participant name and student_id in the document
    def test_participant_details_present(self, tmp_path):
        tpl = tmp_path / "t.hwpx"
        out = tmp_path / "o.hwpx"
        _write_hwpx(tpl, LEGACY_TEMPLATE_XML)

        ctx = self._make_ctx()
        generate_hwpx(tpl, out, ctx, mode="legacy_form")

        text = extract_hwpx_text(out)

        for p in PARTICIPANTS:
            assert p["name"] in text, f"{p['name']} not in output"
            assert p["student_id"] in text, f"{p['student_id']} not in output"

    # Test 5: Activity content not duplicated
    def test_no_duplicate_body(self, tmp_path):
        tpl = tmp_path / "t.hwpx"
        out = tmp_path / "o.hwpx"
        _write_hwpx(tpl, LEGACY_TEMPLATE_XML)

        ctx = self._make_ctx()
        generate_hwpx(tpl, out, ctx, mode="legacy_form")

        text = extract_hwpx_text(out)

        # "1. 활동명" should appear at most once
        first_line = "1. 활동명: 위퍼퓸 교내조향활동"
        occurrences = text.count(first_line)
        assert occurrences <= 1, (
            f"Body content appears {occurrences} times (expected ≤1). Possible duplicate substitution."
        )

    # Full layout scenario test
    def test_full_layout_scenario(self, tmp_path):
        tpl = tmp_path / "t.hwpx"
        out = tmp_path / "o.hwpx"
        _write_hwpx(tpl, LEGACY_TEMPLATE_XML)

        ctx = self._make_ctx()
        result = generate_hwpx(tpl, out, ctx, mode="legacy_form")

        assert out.exists()
        assert result.replaced_count > 0
        assert result.participant_count == 3

        text = extract_hwpx_text(out)

        # Date and count
        assert "2026.06.03" in text
        assert "참여인원 총 3명" in text

        # Example strings gone
        assert "2025.00.00" not in text
        assert "00명" not in text
        assert "동아리 홍보전에 참여하여" not in text

        # Report body lines
        assert "1. 활동명" in text
        assert "5. 활동 목적" in text

        # All participants
        for p in PARTICIPANTS:
            assert p["name"] in text
            assert p["student_id"] in text


# ── Table-structure unit tests ────────────────────────────────────────────────

# HWPX table XML fixture (label cell | value cell)
TABLE_XML = """<hp:sec xmlns:hp="http://www.hancom.co.kr/hwpml/2011">
<hp:tbl>
<hp:tr>
  <hp:tc><hp:p><hp:run><hp:t>활동 장소</hp:t></hp:run></hp:p></hp:tc>
  <hp:tc><hp:p><hp:run><hp:t>종합관 앞</hp:t></hp:run></hp:p></hp:tc>
</hp:tr>
<hp:tr>
  <hp:tc><hp:p><hp:run><hp:t>활동 내용</hp:t></hp:run></hp:p></hp:tc>
  <hp:tc>
    <hp:p><hp:run><hp:t>동아리 홍보전에 참여하여 신입생과 재학생들에게 동아리 가입을 도모하는 활동을 진행함</hp:t></hp:run></hp:p>
    <hp:p><hp:run><hp:t>추가 예시 본문 두번째 단락</hp:t></hp:run></hp:p>
  </hp:tc>
</hp:tr>
</hp:tbl>
<hp:p><hp:run><hp:t>이하 생략</hp:t></hp:run></hp:p>
<hp:p><hp:run><hp:t>참여인원 총 00명</hp:t></hp:run></hp:p>
</hp:sec>"""


class TestTableCellHelpers:
    def test_find_enclosing_table_cell(self):
        m = list(_TEXT_EL_RE.finditer(TABLE_XML))
        # Find "활동 장소" text element
        for tm in m:
            if "활동 장소" in tm.group(1):
                result = _find_enclosing_table_cell(TABLE_XML, tm.start())
                assert result is not None
                _s, _e, tag = result
                assert "tc" in tag.lower()
                break
        else:
            assert False, "활동 장소 text element not found"

    def test_find_enclosing_table_row(self):
        m = list(_TEXT_EL_RE.finditer(TABLE_XML))
        for tm in m:
            if "이하 생략" in tm.group(1):
                result = _find_enclosing_table_row(TABLE_XML, tm.start())
                # "이하 생략" is in a plain <hp:p> outside any <hp:tr> in this fixture
                # So it should NOT find a table row
                assert result is None
                break

    def test_find_next_tc(self):
        # After "활동 장소" tc ends, the next element should be the value cell
        m = list(_TEXT_EL_RE.finditer(TABLE_XML))
        for tm in m:
            if "활동 장소" in tm.group(1):
                tc = _find_enclosing_table_cell(TABLE_XML, tm.start())
                assert tc is not None
                next_tc = _find_next_element(TABLE_XML, tc[1], _TC_OPEN_RE)
                assert next_tc is not None
                # The next cell should contain "종합관 앞"
                next_tc_xml = TABLE_XML[next_tc[0]: next_tc[1]]
                assert "종합관 앞" in next_tc_xml
                break

    def test_get_paragraphs_in_range(self):
        # The "활동 내용" value cell has 2 paragraphs
        for tm in _TEXT_EL_RE.finditer(TABLE_XML):
            if "활동 내용" in tm.group(1):
                tc = _find_enclosing_table_cell(TABLE_XML, tm.start())
                assert tc is not None
                next_tc = _find_next_element(TABLE_XML, tc[1], _TC_OPEN_RE)
                assert next_tc is not None
                paras = _get_paragraphs_in_range(TABLE_XML, next_tc[0], next_tc[1])
                assert len(paras) == 2, f"Expected 2 paragraphs, got {len(paras)}"
                break


class TestTableCellReplacement:
    """Tests that verify table-cell-neighbor replacement works (HWPX form structure)."""

    def test_location_replaced_in_value_cell(self):
        """Location replacement should replace the cell ADJACENT to the label cell."""
        new_xml, count, old = _replace_paragraph_after_heading(TABLE_XML, "활동 장소", ["A401호"])
        assert "A401호" in new_xml, "New location should be present"
        assert "종합관 앞" not in new_xml, "Old location should be gone"
        assert old == "종합관 앞"
        assert count >= 1

    def test_all_example_paragraphs_replaced(self):
        """ALL paragraphs in the value cell should be replaced (not just the first)."""
        lines = ["1. 첫번째 항목", "2. 두번째 항목"]
        new_xml, count, _ = _replace_paragraph_after_heading(TABLE_XML, "활동 내용", lines)

        assert "1. 첫번째 항목" in new_xml
        assert "2. 두번째 항목" in new_xml
        # Both original paragraphs must be gone
        assert "동아리 홍보전에 참여하여" not in new_xml
        assert "추가 예시 본문 두번째 단락" not in new_xml

    def test_count_reflects_paragraphs_inserted(self):
        lines = ["A", "B", "C"]
        _, count, _ = _replace_paragraph_after_heading(TABLE_XML, "활동 내용", lines)
        assert count == 3


class TestTableRowClone:
    """Tests for Method B: table row clone for participant roster."""

    TABLE_ROSTER_XML = """<hp:sec xmlns:hp="http://www.hancom.co.kr/hwpml/2011">
<hp:tbl>
  <hp:tr><hp:tc><hp:p><hp:t>이름</hp:t></hp:p></hp:tc><hp:tc><hp:p><hp:t>학과</hp:t></hp:p></hp:tc><hp:tc><hp:p><hp:t>학번</hp:t></hp:p></hp:tc></hp:tr>
  <hp:tr><hp:tc><hp:p><hp:t>이하 생략</hp:t></hp:p></hp:tc><hp:tc><hp:p><hp:t></hp:t></hp:p></hp:tc><hp:tc><hp:p><hp:t></hp:t></hp:p></hp:tc></hp:tr>
</hp:tbl>
<hp:p><hp:run><hp:t>참여인원 총 00명</hp:t></hp:run></hp:p>
</hp:sec>"""

    TABLE_ROSTER_5_CELL_XML = """<hp:sec xmlns:hp="http://www.hancom.co.kr/hwpml/2011">
<hp:tbl rowCnt="2" colCnt="5">
  <hp:tr><hp:tc><hp:p><hp:t>이름</hp:t></hp:p></hp:tc><hp:tc><hp:p><hp:t>학과</hp:t></hp:p></hp:tc><hp:tc><hp:p><hp:t>학번</hp:t></hp:p></hp:tc><hp:tc><hp:p><hp:t>서명</hp:t></hp:p></hp:tc><hp:tc><hp:p><hp:t>비고</hp:t></hp:p></hp:tc></hp:tr>
  <hp:tr><hp:tc><hp:p><hp:t>이하 생략</hp:t></hp:p></hp:tc><hp:tc><hp:p><hp:t></hp:t></hp:p></hp:tc><hp:tc><hp:p><hp:t></hp:t></hp:p></hp:tc><hp:tc><hp:p><hp:t></hp:t></hp:p></hp:tc><hp:tc><hp:p><hp:t></hp:t></hp:p></hp:tc></hp:tr>
</hp:tbl>
</hp:sec>"""

    def test_table_row_clone_method_b(self):
        """Each participant should get their own cloned <hp:tr> row."""
        new_xml, count = _replace_participant_roster(self.TABLE_ROSTER_XML, PARTICIPANTS)

        assert count == len(PARTICIPANTS), f"Expected {len(PARTICIPANTS)} rows, got {count}"
        # All names and student IDs present
        for p in PARTICIPANTS:
            assert p["name"] in new_xml, f"{p['name']} not in output"
            assert p["student_id"] in new_xml, f"{p['student_id']} not in output"
        # No pipe-join pattern
        assert " | " not in new_xml or PARTICIPANTS[0]["name"] not in new_xml.split(" | ")[0]
        # Original "이하 생략" should be gone
        assert "이하 생략" not in new_xml

    def test_table_row_clone_uses_separate_cells_when_template_has_5_cells(self):
        """A 5-cell participant row must place name/department/student_id in separate cells."""
        new_xml, count = _replace_participant_roster(self.TABLE_ROSTER_5_CELL_XML, PARTICIPANTS)

        assert count == len(PARTICIPANTS)
        rows = re.findall(r'<hp:tr>.*?</hp:tr>', new_xml, re.S)
        first_data_row = next(row for row in rows if "이주현" in row)
        cells = re.findall(r'<hp:tc\b.*?</hp:tc>', first_data_row, re.S)

        assert len(cells) >= 5
        assert "이주현" in cells[0]
        assert "컴퓨터공학부" in cells[1]
        assert "2022130026" in cells[2]
        assert "2022130026" not in cells[0]
        assert "이주현 / 2022130026" not in new_xml


class TestTableEndToEnd:
    """End-to-end tests with table-structured HWPX template."""

    TABLE_TEMPLATE_XML = TABLE_XML

    def _make_ctx(self) -> HwpxContext:
        return HwpxContext(
            activity_title="위퍼퓸 교내조향활동",
            activity_month="06",
            activity_date="2026.06.03",
            activity_location="A401호",
            activity_category="교내 활동 참여",
            report_body=MULTILINE_BODY,
            participant_count=len(PARTICIPANTS),
            participant_list=PARTICIPANTS,
            club_name="Oui Parfum",
        )

    def test_all_value_cell_paragraphs_replaced(self, tmp_path):
        tpl = tmp_path / "table.hwpx"
        out = tmp_path / "output.hwpx"
        _write_hwpx(tpl, self.TABLE_TEMPLATE_XML)

        ctx = self._make_ctx()
        generate_hwpx(tpl, out, ctx, mode="legacy_form")

        text = extract_hwpx_text(out)

        # Original example paragraphs must NOT remain
        assert "동아리 홍보전에 참여하여" not in text
        assert "추가 예시 본문 두번째 단락" not in text

        # New content must be present
        assert "1. 활동명" in text
        assert "5. 활동 목적" in text

    def test_no_duplicate_content_in_table_structure(self, tmp_path):
        tpl = tmp_path / "table.hwpx"
        out = tmp_path / "output.hwpx"
        _write_hwpx(tpl, self.TABLE_TEMPLATE_XML)

        ctx = self._make_ctx()
        generate_hwpx(tpl, out, ctx, mode="legacy_form")

        text = extract_hwpx_text(out)
        first_line = "1. 활동명: 위퍼퓸 교내조향활동"
        assert text.count(first_line) <= 1, (
            f"Duplicate body content: '{first_line}' appeared {text.count(first_line)} times"
        )
