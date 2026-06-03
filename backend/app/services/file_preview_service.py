"""File preview service.

Generates preview metadata for various file types.
Preview failures are caught gracefully and returned as error info.

Supported:
  PDF     → {"type": "pdf", "preview_url": "/api/files/{id}/preview/inline"}
  Image   → {"type": "image", "preview_url": "..."}
  Excel   → {"type": "excel", "sheets": [...]}
  ZIP     → {"type": "zip", "files": [...]}
  HWP/X   → {"type": "hwp", "info": "..."}
  Other   → {"type": "unsupported"}
"""
from __future__ import annotations

from pathlib import Path
from typing import Any


IMAGE_EXTS = {"png", "jpg", "jpeg", "webp", "gif", "bmp", "tiff"}
EXCEL_EXTS = {"xlsx", "xls", "csv"}
HWP_EXTS = {"hwp", "hwpx"}


def build_file_preview(file_id: str, abs_path: Path, ext: str | None, mime_type: str | None) -> dict[str, Any]:
    """Return preview metadata dict for a file.

    Never raises — wraps errors in {"type": "error", "message": ...}.
    """
    ext_clean = (ext or "").lower().lstrip(".")
    if not ext_clean and abs_path:
        ext_clean = abs_path.suffix.lower().lstrip(".")

    try:
        if mime_type and mime_type.startswith("image/"):
            return _preview_image(file_id)
        if ext_clean == "pdf" or (mime_type and "pdf" in mime_type):
            return _preview_pdf(file_id)
        if ext_clean in IMAGE_EXTS:
            return _preview_image(file_id)
        if ext_clean in EXCEL_EXTS:
            return _preview_excel(abs_path, ext_clean)
        if ext_clean == "zip" or (mime_type and "zip" in mime_type):
            return _preview_zip(abs_path)
        if ext_clean in HWP_EXTS:
            return _preview_hwp(abs_path, file_id, ext_clean)
        return {"type": "unsupported", "message": "미리보기를 지원하지 않는 파일 형식입니다."}
    except Exception as exc:  # noqa: BLE001
        return {"type": "error", "message": str(exc)}


def _preview_pdf(file_id: str) -> dict[str, Any]:
    return {
        "type": "pdf",
        "preview_url": f"/api/files/{file_id}/preview/inline",
    }


def _preview_image(file_id: str) -> dict[str, Any]:
    return {
        "type": "image",
        "preview_url": f"/api/files/{file_id}/preview/inline",
    }


def _preview_excel(abs_path: Path, ext: str) -> dict[str, Any]:
    try:
        import pandas as pd  # noqa: PLC0415

        if ext == "csv":
            df = pd.read_csv(abs_path, nrows=30, dtype=str, encoding_errors="replace")
            return {
                "type": "excel",
                "sheets": [
                    {
                        "name": "Sheet1",
                        "headers": list(df.columns),
                        "rows": [
                            [str(v) if v is not None and v == v else "" for v in row]
                            for row in df.values.tolist()[:30]
                        ],
                    }
                ],
            }
        else:
            xl = pd.ExcelFile(abs_path)
            sheets = []
            for sheet_name in xl.sheet_names[:5]:
                df = xl.parse(sheet_name, nrows=30, dtype=str)
                sheets.append(
                    {
                        "name": str(sheet_name),
                        "headers": list(df.columns),
                        "rows": [
                            [str(v) if v is not None and str(v) != "nan" else "" for v in row]
                            for row in df.values.tolist()[:30]
                        ],
                    }
                )
            return {"type": "excel", "sheets": sheets}
    except Exception as exc:  # noqa: BLE001
        return {"type": "error", "message": f"엑셀 미리보기 실패: {exc}"}


def _preview_zip(abs_path: Path) -> dict[str, Any]:
    try:
        import zipfile

        if not abs_path.exists():
            return {"type": "error", "message": "파일을 찾을 수 없습니다."}

        with zipfile.ZipFile(abs_path, "r") as zf:
            file_list = []
            for info in zf.infolist():
                if not info.filename.endswith("/"):
                    file_list.append(
                        {
                            "filename": info.filename,
                            "size_bytes": info.file_size,
                        }
                    )
            return {"type": "zip", "files": file_list[:200]}
    except Exception as exc:  # noqa: BLE001
        return {"type": "error", "message": f"ZIP 미리보기 실패: {exc}"}


def _preview_hwp(abs_path: Path, file_id: str, ext: str) -> dict[str, Any]:
    """HWP/HWPX: return metadata + download guidance."""
    size_bytes = None
    if abs_path.exists():
        size_bytes = abs_path.stat().st_size

    result: dict[str, Any] = {
        "type": "hwp",
        "ext": ext,
        "size_bytes": size_bytes,
        "message": "HWP/HWPX 파일은 미리보기를 지원하지 않습니다. 원본 파일을 다운로드하여 확인하세요.",
        "download_url": f"/api/files/{file_id}/download",
    }

    # Minimal HWPX metadata extraction (XML-based)
    if ext == "hwpx" and abs_path.exists():
        try:
            import zipfile
            import xml.etree.ElementTree as ET  # noqa: N813

            with zipfile.ZipFile(abs_path, "r") as zf:
                names = zf.namelist()
                if "Contents/header.xml" in names:
                    with zf.open("Contents/header.xml") as f:
                        tree = ET.parse(f)
                        root = tree.getroot()
                        ns = {"hh": "http://www.hancom.co.kr/hwpml/2012/head/v2"}
                        title_el = root.find(".//hh:docTitle", ns)
                        if title_el is not None and title_el.text:
                            result["doc_title"] = title_el.text
        except Exception:
            pass

    return result
