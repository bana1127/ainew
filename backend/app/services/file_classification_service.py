"""Rule-based file category/role classifier.

Determines file_category and file_role from filename, extension, mime_type.
Reuses Task 18 excel_form_classifier for Excel files.

file_category values:
  activity_report, activity_plan, receipt, photo,
  google_form_application, google_form_feedback,
  bank_statement, attachment, submission_package, other

file_role values:
  source, evidence, report, plan, attachment, submission, generated
"""
from __future__ import annotations

import re
from dataclasses import dataclass


IMAGE_EXTS = {"png", "jpg", "jpeg", "webp", "gif", "bmp", "tiff", "heic", "heif"}
EXCEL_EXTS = {"xlsx", "xls", "csv"}
HWP_EXTS = {"hwp", "hwpx"}
PDF_EXT = "pdf"
ZIP_EXT = "zip"


@dataclass
class FileClassificationResult:
    file_category: str
    file_role: str
    confidence: float
    reason: str


# Keyword → category mapping (ordered by specificity)
_NAME_RULES: list[tuple[list[str], str, str]] = [
    # (keywords_in_filename, category, role)
    (["내역서", "활동내역"], "activity_report", "report"),
    (["보고서", "활동보고"], "activity_report", "report"),
    (["기획서", "계획서"], "activity_plan", "plan"),
    (["영수증", "receipt", "invoice"], "receipt", "evidence"),
    (["응답", "신청서", "application", "google form"], "google_form_application", "source"),
    (["피드백", "활동지", "feedback", "설문"], "google_form_feedback", "source"),
    (["거래내역", "입출금", "통장", "bank", "statement"], "bank_statement", "source"),
    (["제출패키지", "submission", "패키지", "월별"], "submission_package", "submission"),
]


def classify_uploaded_file(
    filename: str,
    mime_type: str | None = None,
    headers: list[str] | None = None,
) -> FileClassificationResult:
    """Classify a file and return category/role/confidence.

    If headers are provided and the file is an Excel type, Task 18 classifier is used as a hint.
    """
    ext = _get_ext(filename)
    name_lower = filename.lower()

    # ZIP files
    if ext == ZIP_EXT:
        return FileClassificationResult(
            file_category="submission_package",
            file_role="submission",
            confidence=0.9,
            reason="zip 확장자",
        )

    # Image files — receipt or photo
    if ext in IMAGE_EXTS or (mime_type and mime_type.startswith("image/")):
        for kws, cat, role in _NAME_RULES:
            if any(kw in name_lower for kw in kws):
                return FileClassificationResult(
                    file_category=cat,
                    file_role=role,
                    confidence=0.85,
                    reason=f"파일명 키워드 매칭",
                )
        return FileClassificationResult(
            file_category="photo",
            file_role="evidence",
            confidence=0.7,
            reason="이미지 확장자",
        )

    # Excel files — try Task 18 classifier first
    if ext in EXCEL_EXTS:
        if headers is not None:
            try:
                from app.services.excel_form_classifier import classify_excel_form
                result = classify_excel_form(headers, filename)
                category_map = {
                    "activity_application_form": ("google_form_application", "source"),
                    "activity_feedback_form": ("google_form_feedback", "source"),
                    "bank_statement": ("bank_statement", "source"),
                    "member_roster": ("attachment", "source"),
                    "unknown_excel": None,
                }
                if result.form_type in category_map and category_map[result.form_type]:
                    cat, role = category_map[result.form_type]
                    return FileClassificationResult(
                        file_category=cat,
                        file_role=role,
                        confidence=result.confidence,
                        reason=f"Task18 classifier: {result.reason}",
                    )
            except Exception:
                pass
        # Fallback: filename keywords
        for kws, cat, role in _NAME_RULES:
            if any(kw in name_lower for kw in kws):
                return FileClassificationResult(
                    file_category=cat,
                    file_role=role,
                    confidence=0.75,
                    reason="파일명 키워드 (엑셀)",
                )
        return FileClassificationResult(
            file_category="attachment",
            file_role="source",
            confidence=0.5,
            reason="엑셀 확장자, 분류 불명",
        )

    # HWP / HWPX
    if ext in HWP_EXTS:
        for kws, cat, role in _NAME_RULES:
            if any(kw in name_lower for kw in kws):
                return FileClassificationResult(
                    file_category=cat,
                    file_role=role,
                    confidence=0.8,
                    reason="파일명 키워드 (HWP)",
                )
        return FileClassificationResult(
            file_category="activity_report",
            file_role="submission",
            confidence=0.55,
            reason="HWP/HWPX 확장자 (내역서 추정)",
        )

    # PDF
    if ext == PDF_EXT or (mime_type and "pdf" in mime_type):
        for kws, cat, role in _NAME_RULES:
            if any(kw in name_lower for kw in kws):
                return FileClassificationResult(
                    file_category=cat,
                    file_role=role,
                    confidence=0.82,
                    reason="파일명 키워드 (PDF)",
                )
        return FileClassificationResult(
            file_category="attachment",
            file_role="attachment",
            confidence=0.5,
            reason="PDF, 키워드 없음",
        )

    # Generic filename keyword check
    for kws, cat, role in _NAME_RULES:
        if any(kw in name_lower for kw in kws):
            return FileClassificationResult(
                file_category=cat,
                file_role=role,
                confidence=0.65,
                reason="파일명 키워드",
            )

    return FileClassificationResult(
        file_category="other",
        file_role="attachment",
        confidence=0.3,
        reason="분류 규칙 없음",
    )


def _get_ext(filename: str) -> str:
    """Return lowercase extension without leading dot."""
    parts = filename.rsplit(".", 1)
    if len(parts) == 2:
        return parts[1].lower()
    return ""
