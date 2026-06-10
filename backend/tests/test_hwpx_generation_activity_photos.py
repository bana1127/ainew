from __future__ import annotations

import io
import zipfile
from pathlib import Path

from app.services.hwpx_generation_service import HwpxContext, generate_hwpx


ROOT = Path(__file__).resolve().parents[2]
REAL_TEMPLATE = ROOT / "data" / "Oui Parfum_20250000_교내 활동 참여.hwpx"
REAL_ACTIVITY_PHOTO = ROOT / "data" / "활동사진.png"


def _write_hwpx(path: Path, section_xml: str) -> None:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as zf:
        zf.writestr("META-INF/container.xml", "<container/>")
        zf.writestr(
            "Contents/header.xml",
            (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<hh:head xmlns:hh="http://www.hancom.co.kr/hwpml/2011/head">'
                '<hh:refList></hh:refList>'
                '</hh:head>'
            ).encode("utf-8"),
        )
        zf.writestr("Contents/section0.xml", section_xml.encode("utf-8"))
    path.write_bytes(buf.getvalue())


def test_activity_photo_inserted_into_photo_area(tmp_path: Path) -> None:
    tpl = tmp_path / "photo_template.hwpx"
    out = tmp_path / "photo_output.hwpx"
    photo = tmp_path / "activity.jpg"
    photo.write_bytes(b"\xff\xd8\xff\xd9")
    xml = """<hp:sec xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph" xmlns:hc="http://www.hancom.co.kr/hwpml/2011/core">
<hp:p><hp:run><hp:tbl>
<hp:tr><hp:tc><hp:subList><hp:p><hp:run><hp:t>활동 사진</hp:t></hp:run></hp:p></hp:subList></hp:tc></hp:tr>
<hp:tr><hp:tc><hp:subList><hp:p><hp:run charPrIDRef="0"/></hp:p></hp:subList></hp:tc></hp:tr>
</hp:tbl></hp:run></hp:p>
</hp:sec>"""
    _write_hwpx(tpl, xml)

    result = generate_hwpx(
        tpl,
        out,
        HwpxContext(activity_photo_paths=[str(photo)]),
        mode="legacy_form",
    )

    assert result.replaced_count >= 1
    with zipfile.ZipFile(out) as zf:
        names = set(zf.namelist())
        section = zf.read("Contents/section0.xml").decode("utf-8")
        header = zf.read("Contents/header.xml").decode("utf-8")

    assert "BinData/activity_photo_1.jpg" in names
    assert "<hp:pic" in section
    assert 'binaryItemIDRef="activityPhoto1"' in section
    assert '<hh:binData itemCnt="1">' in header
    assert 'id="activityPhoto1"' in header
    assert 'embedding="BinData/activity_photo_1.jpg"' in header
    assert 'mediaType="image/jpeg"' in header


def test_real_template_embeds_data_activity_photo(tmp_path: Path) -> None:
    assert REAL_TEMPLATE.exists()
    assert REAL_ACTIVITY_PHOTO.exists()

    out = tmp_path / "real_photo_output.hwpx"
    result = generate_hwpx(
        REAL_TEMPLATE,
        out,
        HwpxContext(activity_photo_paths=[str(REAL_ACTIVITY_PHOTO)]),
        mode="legacy_form",
    )

    assert result.replaced_count >= 1
    assert not any("활동 사진을 넣을 영역" in warning for warning in result.warnings)

    with zipfile.ZipFile(out) as zf:
        names = set(zf.namelist())
        section = zf.read("Contents/section0.xml").decode("utf-8")
        header = zf.read("Contents/header.xml").decode("utf-8")
        content_hpf = zf.read("Contents/content.hpf").decode("utf-8")

    assert "BinData/activity_photo_1.png" in names
    assert '<hp:pic' in section
    assert 'binaryItemIDRef="activityPhoto1"' in section
    assert '<hp:curSz width="40932" height="22000"/>' in section
    assert '<hp:orgSz width="40932" height="22000"/>' in section
    assert '<hp:imgClip left="0" right="40932" top="0" bottom="22000"/>' in section
    assert '<hh:binData itemCnt="1">' in header
    assert 'embedding="BinData/activity_photo_1.png"' in header
    assert 'mediaType="image/png"' in header
    assert 'href="BinData/activity_photo_1.png"' in content_hpf
