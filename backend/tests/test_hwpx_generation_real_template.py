# -*- coding: utf-8 -*-
from __future__ import annotations

import zipfile
from pathlib import Path

from app.services.hwpx_generation_service import (
    HwpxContext,
    _TEXT_EL_RE,
    _iter_cells,
    _iter_rows,
    _iter_tables,
    extract_hwpx_text,
    generate_hwpx,
)


ROOT = Path(__file__).resolve().parents[2]
REAL_TEMPLATE = ROOT / "data" / "Oui Parfum_20250000_교내 활동 참여.hwpx"


PARTICIPANTS = [
    {"name": "이주현", "department": "컴퓨터공학부", "student_id": "2022130026", "note": ""},
    {"name": "심사무엘", "department": "사무행정학과", "student_id": "2022200032", "note": ""},
    {"name": "박민서", "department": "향장학과", "student_id": "2023000003", "note": ""},
    {"name": "김가은", "department": "경영학과", "student_id": "2023000004", "note": ""},
    {"name": "이도윤", "department": "컴퓨터공학부", "student_id": "2023000005", "note": ""},
    {"name": "문채영", "department": "디자인학부", "student_id": "2023000006", "note": ""},
    {"name": "최서연", "department": "화학과", "student_id": "2023000007", "note": ""},
    {"name": "정하준", "department": "경영학과", "student_id": "2023000008", "note": ""},
    {"name": "한지우", "department": "전자공학부", "student_id": "2023000009", "note": ""},
    {"name": "윤서진", "department": "컴퓨터공학부", "student_id": "2023000010", "note": ""},
    {"name": "강민준", "department": "기계공학부", "student_id": "2023000011", "note": ""},
    {"name": "오수빈", "department": "국문학과", "student_id": "2023000012", "note": ""},
    {"name": "임도현", "department": "경제학과", "student_id": "2023000013", "note": ""},
    {"name": "서지민", "department": "영문학과", "student_id": "2023000014", "note": ""},
    {"name": "조예린", "department": "교육학과", "student_id": "2023000015", "note": ""},
    {"name": "남현우", "department": "화학과", "student_id": "2023000016", "note": ""},
    {"name": "배유나", "department": "디자인학부", "student_id": "2023000017", "note": ""},
    {"name": "신재윤", "department": "전자공학부", "student_id": "2023000018", "note": ""},
    {"name": "권하린", "department": "경영학과", "student_id": "2023000019", "note": ""},
]


REPORT_BODY = "\n".join(
    [
        "1. 활동명: 위퍼퓸 교내조향활동",
        "2. 활동 일시: 2026년 6월 3일",
        "3. 활동 장소: A401호",
        "4. 참석자: 참여인원 총 19명",
        "5. 활동 목적: 조향 체험과 동아리 활동 홍보",
        "6. 주요 내용: 향료 소개, 시향, 블렌딩 실습을 진행함",
        "7. 활동 결과: 참여자들이 완성 향을 공유하고 활동 이해도가 높아짐",
        "8. 향후 계획: 정기 조향 실습으로 후속 활동을 이어감",
    ]
)


def _ctx() -> HwpxContext:
    return HwpxContext(
        activity_title="위퍼퓸 교내조향활동",
        activity_month="06",
        activity_date="2026.06.03",
        activity_location="A401호",
        activity_category="교내 활동 참여",
        report_body=REPORT_BODY,
        participant_count=len(PARTICIPANTS),
        participant_list=PARTICIPANTS,
        club_name="Oui Parfum",
    )


def _section_xml(path: Path) -> str:
    with zipfile.ZipFile(path, "r") as zf:
        return zf.read("Contents/section0.xml").decode("utf-8", errors="replace")


def _participant_rows(xml: str) -> list[str]:
    for _tbl_start, _tbl_end, table_xml in _iter_tables(xml):
        rows = [row for _s, _e, row in _iter_rows(table_xml)]
        header_idx = None
        for idx, row in enumerate(rows):
            texts = [m.group(1).strip() for m in _TEXT_EL_RE.finditer(row) if m.group(1).strip()]
            if all(label in texts for label in ("이름", "학과", "학번", "서명", "비고")):
                header_idx = idx
                break
        if header_idx is None:
            continue
        return [row for row in rows[header_idx + 1:] if any(p["name"] in row for p in PARTICIPANTS)]
    return []


def test_real_oui_parfum_template_generates_structured_hwpx(tmp_path: Path):
    assert REAL_TEMPLATE.exists()
    out = tmp_path / "generated.hwpx"

    result = generate_hwpx(REAL_TEMPLATE, out, _ctx())

    assert out.exists()
    assert result.participant_count == 19

    text = extract_hwpx_text(out)
    xml = _section_xml(out)

    assert text.count("1. 활동명:") == 1
    assert "1. 활동명: 위퍼퓸 교내조향활동2. 활동 일시:" not in text
    assert REPORT_BODY not in xml

    for label in (
        "1. 활동명:",
        "2. 활동 일시:",
        "3. 활동 장소:",
        "4. 참석자:",
        "5. 활동 목적:",
        "6. 주요 내용:",
        "7. 활동 결과:",
        "8. 향후 계획:",
    ):
        assert label in text

    rows = _participant_rows(xml)
    assert len(rows) == len(PARTICIPANTS)
    for row in rows:
        assert len(_iter_cells(row)) >= 5

    first_row = rows[0]
    cells = [cell for _s, _e, cell in _iter_cells(first_row)]
    assert "이주현" in cells[0]
    assert "2022130026" in cells[2]
    assert "2022130026" not in cells[0]
    assert "이주현 / 2022130026" not in text
    assert "이주현  /  2022130026" not in text

    assert "2025.00.00" not in text
    assert "종합관 앞" not in text
    assert "참여인원 총 00명" not in text
    assert "참여인원 총 19명" in text
