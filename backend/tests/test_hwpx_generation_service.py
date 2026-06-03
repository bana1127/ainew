# -*- coding: utf-8 -*-
"""Tests for hwpx_generation_service (Task 24).

All tests work without a live database or HWPX file by constructing
minimal in-memory HWPX (zip + XML) fixtures.

Test coverage:
  1. Legacy form mode — 00월, date, location, count replaced
  2. Report body reflected (example text gone)
  3. Participant roster reflected
  4. Placeholder mode — {{key}} substituted
  5. Template-copy prevention — no raw example strings survive
  6. extract_hwpx_text — returns correct plain text
  7. detect_template_mode — placeholder vs legacy
"""
from __future__ import annotations

import io
import re
import zipfile
from pathlib import Path

import pytest

from app.services.hwpx_generation_service import (
    HwpxContext,
    _apply_legacy_mode,
    _apply_placeholder_mode,
    _replace_participant_roster,
    _replace_text_after_heading,
    detect_template_mode,
    extract_hwpx_text,
    generate_hwpx,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_hwpx(section_xml: str) -> bytes:
    """Build a minimal in-memory HWPX (zip) with one section XML."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as zf:
        zf.writestr("META-INF/container.xml", "<container/>")
        zf.writestr("Contents/section0.xml", section_xml.encode("utf-8"))
    return buf.getvalue()


def _xml_wrap(text: str, ns: str = "hp") -> str:
    """Wrap plain text in a minimal HWPX section XML structure."""
    return (
        f'<?xml version="1.0" encoding="UTF-8"?>'
        f'<{ns}:sec xmlns:{ns}="http://www.hancom.co.kr/hwpml/2011/paragraph">'
        f'<{ns}:p><{ns}:run><{ns}:t>{text}</{ns}:t></{ns}:run></{ns}:p>'
        f'</{ns}:sec>'
    )


def _write_hwpx(path: Path, section_xml: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_make_hwpx(section_xml))


# ── Test 6. extract_hwpx_text ─────────────────────────────────────────────────

class TestExtractHwpxText:
    def test_extracts_text_nodes(self, tmp_path):
        content = "안녕 Oui Parfum 테스트 문서"
        p = tmp_path / "t.hwpx"
        _write_hwpx(p, _xml_wrap(content))
        result = extract_hwpx_text(p)
        assert "안녕" in result
        assert "Oui Parfum" in result

    def test_multi_text_elements(self, tmp_path):
        xml = (
            '<hp:sec xmlns:hp="x">'
            '<hp:p><hp:run><hp:t>첫번째</hp:t><hp:t>두번째</hp:t></hp:run></hp:p>'
            '</hp:sec>'
        )
        p = tmp_path / "t.hwpx"
        _write_hwpx(p, xml)
        result = extract_hwpx_text(p)
        assert "첫번째" in result
        assert "두번째" in result


# ── Test 7. detect_template_mode ─────────────────────────────────────────────

class TestDetectTemplateMode:
    def test_placeholder_mode(self, tmp_path):
        p = tmp_path / "t.hwpx"
        _write_hwpx(p, _xml_wrap("{{활동명}} {{활동일}}"))
        assert detect_template_mode(p) == "placeholder"

    def test_legacy_mode(self, tmp_path):
        p = tmp_path / "t.hwpx"
        _write_hwpx(p, _xml_wrap("00월 [ Test ] 동아리 활동 내역서\n2025.00.00\n참여인원 총 00명"))
        assert detect_template_mode(p) == "legacy_form"

    def test_mixed_mode(self, tmp_path):
        p = tmp_path / "t.hwpx"
        _write_hwpx(p, _xml_wrap("{{활동명}}\n00월 동아리 활동\n2025.00.00"))
        assert detect_template_mode(p) == "mixed"


# ── Pure function tests ──────────────────────────────────────────────────────

class TestApplyLegacyMode:
    def _ctx(self, **kw) -> HwpxContext:
        defaults = dict(
            activity_title="위퍼퓸 교내조향활동",
            activity_month="06",
            activity_date="2026.06.03",
            activity_location="A401호",
            activity_category="교내 활동 참여",
            report_body="이번 활동은 교내 조향 체험을 중심으로 진행되었다.",
            participant_count=19,
            participant_list=[],
            club_name="Oui Parfum",
        )
        defaults.update(kw)
        return HwpxContext(**defaults)

    # Test 1: Legacy form replacements
    def test_month_replaced(self):
        xml = "<t>00월 [ Oui Parfum ] 동아리 활동 내역서</t>"
        ctx = self._ctx()
        new_xml, count, _ = _apply_legacy_mode(xml, ctx)
        assert "06월" in new_xml
        assert "00월" not in new_xml
        assert count >= 1

    def test_date_replaced(self):
        xml = "<t>2025.00.00</t>"
        ctx = self._ctx()
        new_xml, count, _ = _apply_legacy_mode(xml, ctx)
        assert "2026.06.03" in new_xml
        assert "2025.00.00" not in new_xml

    def test_participant_count_replaced(self):
        xml = "<t>참여인원 총 00명</t>"
        ctx = self._ctx(participant_count=19)
        new_xml, count, _ = _apply_legacy_mode(xml, ctx)
        assert "참여인원 총 19명" in new_xml
        assert "00명" not in new_xml

    def test_location_replaced_after_heading(self):
        xml = (
            "<hp:sec>"
            "<hp:p><hp:t>활동 장소</hp:t></hp:p>"
            "<hp:p><hp:t>종합관 앞</hp:t></hp:p>"
            "</hp:sec>"
        )
        ctx = self._ctx(activity_location="A401호")
        new_xml, count, _ = _apply_legacy_mode(xml, ctx)
        assert "A401호" in new_xml
        assert count >= 1

    def test_category_replaced_after_heading(self):
        xml = (
            "<sec>"
            "<p><t>활동 분류</t></p>"
            "<p><t>제89조 7항 교내 활동 참여</t></p>"
            "</sec>"
        )
        ctx = self._ctx(activity_category="교내 활동 참여 (제89조)")
        new_xml, count, _ = _apply_legacy_mode(xml, ctx)
        assert "교내 활동 참여 (제89조)" in new_xml
        assert count >= 1

    # Test 2: Report body reflected + example text gone
    def test_body_replaced_after_heading(self):
        example_body = "동아리 홍보전에 참여하여 신입생과 재학생들에게 동아리 가입을 도모하는 활동을 진행함"
        xml = (
            "<sec>"
            "<p><t>활동 내용</t></p>"
            f"<p><t>{example_body}</t></p>"
            "</sec>"
        )
        new_body = "이번 활동은 교내 조향 체험을 중심으로 진행되었다."
        ctx = self._ctx(report_body=new_body)
        new_xml, count, _ = _apply_legacy_mode(xml, ctx)
        assert new_body in new_xml
        assert "동아리 홍보전에 참여하여" not in new_xml
        assert count >= 1

    def test_mappings_returned(self):
        xml = "<t>00월</t>"
        ctx = self._ctx()
        _, _, mappings = _apply_legacy_mode(xml, ctx)
        fields = [m["field"] for m in mappings]
        assert "activity_month" in fields


# ── Test 3: Participant roster ────────────────────────────────────────────────

class TestReplaceParticipantRoster:
    def test_replaces_이하생략(self):
        xml = "<t>이하 생략</t>"
        participants = [
            {"name": "박민서", "department": "컴퓨터공학부", "student_id": "2025170011"},
            {"name": "문채영", "department": "경영학과", "student_id": "2025440012"},
        ]
        new_xml, count = _replace_participant_roster(xml, participants)
        assert "박민서" in new_xml
        assert "2025170011" in new_xml
        assert "문채영" in new_xml
        assert "2025440012" in new_xml
        assert "이하 생략" not in new_xml
        assert count == 1

    def test_no_marker_no_change(self):
        xml = "<t>참여자 명단 없음</t>"
        new_xml, count = _replace_participant_roster(xml, [{"name": "박민서"}])
        assert new_xml == xml
        assert count == 0

    def test_sorted_by_student_id(self):
        xml = "<t>이하 생략</t>"
        participants = [
            {"name": "문채영", "department": "", "student_id": "2025440012"},
            {"name": "박민서", "department": "", "student_id": "2025170011"},
        ]
        new_xml, _ = _replace_participant_roster(xml, participants)
        # 2025170011 (박민서) should appear before 2025440012 (문채영)
        assert new_xml.index("2025170011") < new_xml.index("2025440012")


# ── Test 4: Placeholder mode ──────────────────────────────────────────────────

class TestApplyPlaceholderMode:
    def test_basic_placeholder(self):
        xml = "<t>{{활동명}} - {{활동일}}</t>"
        ctx = HwpxContext(
            activity_title="위퍼퓸 교내조향활동",
            activity_date="2026.06.03",
        )
        mapped: dict = {}
        missing: list = []
        new_xml, count, mappings = _apply_placeholder_mode(xml, ctx, mapped, missing)
        assert "위퍼퍼퓸 교내조향활동" not in new_xml  # sanity
        assert "위퍼퓸 교내조향활동" in new_xml
        assert "2026.06.03" in new_xml
        assert "{{활동명}}" not in new_xml
        assert count == 2

    def test_participant_count_placeholder(self):
        xml = "<t>총 {{참여자수}}명</t>"
        ctx = HwpxContext(participant_count=19)
        new_xml, count, _ = _apply_placeholder_mode(xml, ctx, {}, [])
        assert "총 19명" in new_xml

    def test_unknown_placeholder_becomes_미입력(self):
        xml = "<t>{{알수없는필드}}</t>"
        ctx = HwpxContext()
        new_xml, count, _ = _apply_placeholder_mode(xml, ctx, {}, [])
        assert "(미입력)" in new_xml

    def test_club_name_placeholder(self):
        xml = "<t>{{동아리명}}</t>"
        ctx = HwpxContext(club_name="Oui Parfum")
        new_xml, _, _ = _apply_placeholder_mode(xml, ctx, {}, [])
        assert "Oui Parfum" in new_xml


# ── Test 5: Template-copy prevention ─────────────────────────────────────────

class TestTemplateCopyPrevention:
    """Full end-to-end generation test: example strings must not survive."""

    LEGACY_TEMPLATE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<hp:sec xmlns:hp="http://test">
<hp:p><hp:run><hp:t>00월 [ Oui Parfum ] 동아리 활동 내역서</hp:t></hp:run></hp:p>
<hp:p><hp:run><hp:t>활동 장소</hp:t></hp:run></hp:p>
<hp:p><hp:run><hp:t>종합관 앞</hp:t></hp:run></hp:p>
<hp:p><hp:run><hp:t>활동 일시</hp:t></hp:run></hp:p>
<hp:p><hp:run><hp:t>2025.00.00</hp:t></hp:run></hp:p>
<hp:p><hp:run><hp:t>활동 내용</hp:t></hp:run></hp:p>
<hp:p><hp:run><hp:t>동아리 홍보전에 참여하여 신입생과 재학생들에게 동아리 가입을 도모하는 활동을 진행함</hp:t></hp:run></hp:p>
<hp:p><hp:run><hp:t>이하 생략</hp:t></hp:run></hp:p>
<hp:p><hp:run><hp:t>참여인원 총 00명</hp:t></hp:run></hp:p>
</hp:sec>"""

    def test_legacy_replacements_in_generated_file(self, tmp_path):
        tpl = tmp_path / "template.hwpx"
        out = tmp_path / "output.hwpx"
        _write_hwpx(tpl, self.LEGACY_TEMPLATE_XML)

        ctx = HwpxContext(
            activity_title="위퍼퓸 교내조향활동",
            activity_month="06",
            activity_date="2026.06.03",
            activity_location="A401호",
            activity_category="교내 활동 참여",
            report_body="이번 활동은 교내 조향 체험을 중심으로 진행되었다.",
            participant_count=19,
            participant_list=[
                {"name": "박민서", "department": "컴퓨터공학부", "student_id": "2025170011"},
                {"name": "문채영", "department": "경영학과", "student_id": "2025440012"},
            ],
            club_name="Oui Parfum",
        )

        result = generate_hwpx(tpl, out, ctx, mode="legacy_form")
        assert out.exists(), "Output HWPX must be created"

        text = extract_hwpx_text(out)

        # ── Test 1: date, month, count present ──
        assert "06월" in text, f"Month not found in: {text}"
        assert "2026.06.03" in text, f"Date not found in: {text}"
        assert "참여인원 총 19명" in text, f"Count not found in: {text}"

        # ── Test 1: example values gone ──
        assert "2025.00.00" not in text, f"Old date still present: {text}"
        assert "00명" not in text, f"Old count still present: {text}"

        # ── Test 2: body reflected ──
        assert "교내 조향 체험" in text, f"Report body not found: {text}"
        assert "동아리 홍보전에 참여하여" not in text, f"Example body still present: {text}"

        # ── Test 3: participant roster ──
        assert "박민서" in text, f"Participant not found: {text}"
        assert "2025170011" in text, f"Student ID not found: {text}"
        assert "문채영" in text, f"Participant not found: {text}"

    def test_placeholder_mode_generates_correctly(self, tmp_path):
        ph_xml = """<?xml version="1.0" encoding="UTF-8"?>
<hp:sec xmlns:hp="http://test">
<hp:p><hp:run><hp:t>{{활동명}}</hp:t></hp:run></hp:p>
<hp:p><hp:run><hp:t>{{활동일}}</hp:t></hp:run></hp:p>
<hp:p><hp:run><hp:t>{{보고서본문}}</hp:t></hp:run></hp:p>
<hp:p><hp:run><hp:t>총 {{참여자수}}명</hp:t></hp:run></hp:p>
</hp:sec>"""
        tpl = tmp_path / "ph_template.hwpx"
        out = tmp_path / "ph_output.hwpx"
        _write_hwpx(tpl, ph_xml)

        ctx = HwpxContext(
            activity_title="위퍼퓸 교내조향활동",
            activity_date="2026.06.03",
            report_body="이번 활동은 교내 조향 체험을 중심으로 진행되었다.",
            participant_count=19,
        )

        result = generate_hwpx(tpl, out, ctx, mode="placeholder")
        assert out.exists()
        text = extract_hwpx_text(out)

        assert "위퍼퓸 교내조향활동" in text
        assert "2026.06.03" in text
        assert "교내 조향 체험" in text
        assert "총 19명" in text
        assert "{{" not in text, "Unresolved placeholders remain"


# ── Test: _replace_text_after_heading (unit) ──────────────────────────────────

class TestReplaceTextAfterHeading:
    def test_replaces_next_text(self):
        xml = (
            "<sec>"
            "<p><t>활동 장소</t></p>"
            "<p><t>종합관 앞</t></p>"
            "</sec>"
        )
        new_xml, count, old = _replace_text_after_heading(xml, "활동 장소", "A401호")
        assert "A401호" in new_xml
        assert "종합관 앞" not in new_xml
        assert old == "종합관 앞"
        assert count == 1

    def test_no_heading_no_change(self):
        xml = "<p><t>무관한 텍스트</t></p>"
        new_xml, count, old = _replace_text_after_heading(xml, "활동 장소", "A401호")
        assert new_xml == xml
        assert count == 0
