# -*- coding: utf-8 -*-
"""Tests for HWPX layout stability (Task 32).

Validates:
1. _truncate_body_for_form reduces long bodies to ≤4 sentences
2. Participant lists are stripped from body text
3. Numbered items are stripped from body
4. Hard char limit enforced
5. _split_report_body returns form-safe lines
6. generate_hwpx: no template example values remain
7. generate_hwpx: body not duplicated
8. _validate_generation warns on remaining example values
9. Preview mappings include layout warnings for long body
10. Preview mappings include participant count warning
"""
from __future__ import annotations

import io
import re
import zipfile
from pathlib import Path

import pytest

from app.services.hwpx_generation_service import (
    HwpxContext,
    _split_report_body,
    _truncate_body_for_form,
    _validate_generation,
    build_preview_mappings,
    extract_hwpx_text,
    generate_hwpx,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_hwpx(section_xml: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as zf:
        zf.writestr("META-INF/container.xml", "<container/>")
        zf.writestr("Contents/section0.xml", section_xml.encode("utf-8"))
    return buf.getvalue()


def _write_hwpx(path: Path, section_xml: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_make_hwpx(section_xml))


def _oui_parfum_like_xml(
    date: str = "2025.00.00",
    location: str = "종합관 앞",
    participant_count: str = "참여인원 총 00명",
    body: str = "동아리 홍보전에 참여하여",
    include_participant_table: bool = True,
) -> str:
    table_rows = ""
    if include_participant_table:
        table_rows = f"""
        <hp:tr>
          <hp:tc><hp:p><hp:run><hp:t>이름</hp:t></hp:run></hp:p></hp:tc>
          <hp:tc><hp:p><hp:run><hp:t>학과</hp:t></hp:run></hp:p></hp:tc>
          <hp:tc><hp:p><hp:run><hp:t>학번</hp:t></hp:run></hp:p></hp:tc>
          <hp:tc><hp:p><hp:run><hp:t>서명</hp:t></hp:run></hp:p></hp:tc>
          <hp:tc><hp:p><hp:run><hp:t>비고</hp:t></hp:run></hp:p></hp:tc>
        </hp:tr>
        <hp:tr>
          <hp:tc><hp:p><hp:run><hp:t>이하 생략</hp:t></hp:run></hp:p></hp:tc>
          <hp:tc><hp:p><hp:run><hp:t></hp:t></hp:run></hp:p></hp:tc>
          <hp:tc><hp:p><hp:run><hp:t></hp:t></hp:run></hp:p></hp:tc>
          <hp:tc><hp:p><hp:run><hp:t></hp:t></hp:run></hp:p></hp:tc>
          <hp:tc><hp:p><hp:run><hp:t></hp:t></hp:run></hp:p></hp:tc>
        </hp:tr>"""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<hp:sec xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph">
  <hp:p><hp:run><hp:t>동아리 활동 내역서</hp:t></hp:run></hp:p>
  <hp:tbl rowCnt="3">
    <hp:tr>
      <hp:tc><hp:p><hp:run><hp:t>활동 일자</hp:t></hp:run></hp:p></hp:tc>
      <hp:tc><hp:p><hp:run><hp:t>{date}</hp:t></hp:run></hp:p></hp:tc>
    </hp:tr>
    <hp:tr>
      <hp:tc><hp:p><hp:run><hp:t>활동 장소</hp:t></hp:run></hp:p></hp:tc>
      <hp:tc><hp:p><hp:run><hp:t>{location}</hp:t></hp:run></hp:p></hp:tc>
    </hp:tr>
    <hp:tr>
      <hp:tc><hp:p><hp:run><hp:t>00월</hp:t></hp:run></hp:p></hp:tc>
      <hp:tc><hp:p><hp:run><hp:t></hp:t></hp:run></hp:p></hp:tc>
    </hp:tr>
  </hp:tbl>
  <hp:p><hp:run><hp:t>{participant_count}</hp:t></hp:run></hp:p>
  <hp:tbl rowCnt="2">
    <hp:tr>
      <hp:tc><hp:p><hp:run><hp:t>활동 내용</hp:t></hp:run></hp:p></hp:tc>
      <hp:tc><hp:p><hp:run><hp:t>{body}</hp:t></hp:run></hp:p></hp:tc>
    </hp:tr>
  </hp:tbl>
  <hp:p><hp:run><hp:t>참여 인원 명단</hp:t></hp:run></hp:p>
  <hp:tbl rowCnt="3">
    {table_rows}
  </hp:tbl>
</hp:sec>"""


# ── Tests: _truncate_body_for_form ────────────────────────────────────────────

def test_truncate_removes_participant_lines():
    body = "활동 요약 문장입니다.\n참석자: 홍길동, 김영희\n이름 학번 서명"
    result = _truncate_body_for_form(body)
    assert "참석자" not in result
    assert "이름" not in result


def test_truncate_removes_numbered_prefix():
    body = "1. 활동 목적\n2. 진행 방식\n3. 결론"
    result = _truncate_body_for_form(body)
    assert "1." not in result
    assert "활동 목적" in result


def test_truncate_max_sentences():
    body = "문장1. 문장2. 문장3. 문장4. 문장5. 문장6."
    result = _truncate_body_for_form(body, max_sentences=4)
    # Should have at most 4 sentences
    count = len(re.findall(r'문장\d\.', result))
    assert count <= 4


def test_truncate_char_limit():
    body = "가" * 300
    result = _truncate_body_for_form(body)
    assert len(result) <= 200


def test_truncate_empty_body():
    assert _truncate_body_for_form("") == ""


def test_split_report_body_uses_truncated_content():
    # A very long body should produce lines from the truncated version
    body = "긴 문장입니다. " * 20
    lines = _split_report_body(body)
    total_chars = sum(len(l) for l in lines)
    assert total_chars <= 210  # 200 limit + possible "..."


# ── Tests: _validate_generation ──────────────────────────────────────────────

def test_validate_warns_on_example_date():
    warnings: list[str] = []
    ctx = HwpxContext(activity_date="2026.06.03")
    _validate_generation("2025.00.00", ctx, warnings)
    assert any("템플릿 예시값" in w for w in warnings)


def test_validate_warns_on_location_예시():
    warnings: list[str] = []
    ctx = HwpxContext(activity_location="운동장")
    _validate_generation("종합관 앞", ctx, warnings)
    assert any("템플릿 예시값" in w for w in warnings)


def test_validate_warns_on_00명():
    warnings: list[str] = []
    ctx = HwpxContext(participant_count=5)
    _validate_generation("참여인원 총 00명", ctx, warnings)
    assert any("템플릿 예시값" in w for w in warnings)


def test_validate_warns_on_body_duplication():
    warnings: list[str] = []
    ctx = HwpxContext(report_body="활동 설명 텍스트입니다.")
    # Body snippet appears twice
    _validate_generation("활동 설명 텍스트입니다. 활동 설명 텍스트입니다.", ctx, warnings)
    assert any("중복" in w for w in warnings)


def test_validate_no_warnings_when_clean():
    warnings: list[str] = []
    ctx = HwpxContext(
        activity_date="2026.06.03",
        activity_location="운동장",
        participant_count=3,
        report_body="활동 설명 텍스트입니다.",
    )
    text = "2026.06.03 운동장 참여인원 총 3명 활동 설명 텍스트입니다."
    _validate_generation(text, ctx, warnings)
    # No template example warnings
    assert not any("템플릿 예시값" in w for w in warnings)
    assert not any("중복" in w for w in warnings)


# ── Tests: generate_hwpx ─────────────────────────────────────────────────────

def test_generate_hwpx_removes_example_values(tmp_path: Path):
    """Generated HWPX must not contain template example values."""
    tpl_path = tmp_path / "template.hwpx"
    out_path = tmp_path / "output.hwpx"
    _write_hwpx(tpl_path, _oui_parfum_like_xml())

    ctx = HwpxContext(
        activity_title="조향 체험 활동",
        activity_date="2026.06.03",
        activity_month="06",
        activity_location="동아리방",
        report_body="본 활동은 조향 체험을 중심으로 진행되었습니다.",
        participant_count=3,
        participant_list=[
            {"name": "홍길동", "department": "컴퓨터공학과", "student_id": "2022001", "note": ""},
            {"name": "김영희", "department": "전자공학과", "student_id": "2022002", "note": ""},
            {"name": "이철수", "department": "기계공학과", "student_id": "2022003", "note": ""},
        ],
    )

    generate_hwpx(tpl_path, out_path, ctx)
    assert out_path.exists()

    text = extract_hwpx_text(out_path)
    assert "2025.00.00" not in text, "Template date example remains"
    assert "참여인원 총 00명" not in text, "Template count example remains"
    assert "이하 생략" not in text, "이하 생략 should be replaced with participants"


def test_generate_hwpx_participant_count_correct(tmp_path: Path):
    tpl_path = tmp_path / "template.hwpx"
    out_path = tmp_path / "output.hwpx"
    _write_hwpx(tpl_path, _oui_parfum_like_xml())

    participants = [
        {"name": f"참가자{i}", "department": "컴퓨터공학과", "student_id": f"202200{i}", "note": ""}
        for i in range(1, 6)
    ]
    ctx = HwpxContext(
        activity_date="2026.06.03",
        activity_month="06",
        activity_location="동아리방",
        report_body="활동 설명입니다.",
        participant_count=5,
        participant_list=participants,
    )

    generate_hwpx(tpl_path, out_path, ctx)
    text = extract_hwpx_text(out_path)
    assert "참여인원 총 5명" in text


def test_generate_hwpx_body_not_duplicated(tmp_path: Path):
    """Activity body must appear only once in the output."""
    tpl_path = tmp_path / "template.hwpx"
    out_path = tmp_path / "output.hwpx"
    _write_hwpx(tpl_path, _oui_parfum_like_xml())

    unique_snippet = "UNIQUE_BODY_TEXT_XYZ"
    ctx = HwpxContext(
        activity_date="2026.06.03",
        activity_month="06",
        activity_location="동아리방",
        report_body=f"{unique_snippet} 본 활동은 진행되었습니다.",
        participant_count=1,
        participant_list=[{"name": "홍길동", "department": "IT", "student_id": "2022001", "note": ""}],
    )

    generate_hwpx(tpl_path, out_path, ctx)
    text = extract_hwpx_text(out_path)
    count = text.count(unique_snippet)
    assert count <= 1, f"Body snippet appeared {count} times — duplication detected"


def test_generate_hwpx_participant_names_in_separate_cells(tmp_path: Path):
    """Each participant should have name and student_id in SEPARATE cells (not joined)."""
    tpl_path = tmp_path / "template.hwpx"
    out_path = tmp_path / "output.hwpx"
    _write_hwpx(tpl_path, _oui_parfum_like_xml())

    ctx = HwpxContext(
        activity_date="2026.06.03",
        activity_month="06",
        activity_location="동아리방",
        report_body="활동 설명입니다.",
        participant_count=2,
        participant_list=[
            {"name": "홍길동", "department": "IT", "student_id": "2022001", "note": ""},
            {"name": "김영희", "department": "IT", "student_id": "2022002", "note": ""},
        ],
    )

    generate_hwpx(tpl_path, out_path, ctx)
    text = extract_hwpx_text(out_path)
    # Names should appear
    assert "홍길동" in text
    assert "2022001" in text
    # Should NOT have "홍길동 / 2022001" combined in one text node
    assert "홍길동 / 2022001" not in text


# ── Tests: build_preview_mappings warnings ────────────────────────────────────

def test_preview_warns_on_long_body(tmp_path: Path):
    tpl_path = tmp_path / "template.hwpx"
    _write_hwpx(tpl_path, _oui_parfum_like_xml())

    ctx = HwpxContext(
        activity_date="2026.06.03",
        activity_month="06",
        report_body="가" * 300,
        participant_count=5,
        participant_list=[
            {"name": f"참가자{i}", "department": "IT", "student_id": f"20220{i:02d}", "note": ""}
            for i in range(1, 6)
        ],
    )

    _mode, _mappings, warnings = build_preview_mappings(tpl_path, ctx)
    assert any("요약됩니다" in w for w in warnings)


def test_preview_warns_participant_count(tmp_path: Path):
    tpl_path = tmp_path / "template.hwpx"
    _write_hwpx(tpl_path, _oui_parfum_like_xml())

    ctx = HwpxContext(
        activity_date="2026.06.03",
        activity_month="06",
        report_body="활동 설명.",
        participant_count=19,
        participant_list=[
            {"name": f"참가자{i}", "department": "IT", "student_id": f"2022{i:03d}", "note": ""}
            for i in range(1, 20)
        ],
    )

    _mode, _mappings, warnings = build_preview_mappings(tpl_path, ctx)
    assert any("19명" in w for w in warnings)
