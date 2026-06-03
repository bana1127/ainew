"""HWPX document generation service (Task 24).

Supports two modes:
1. Placeholder mode  — {{key}} substitution in XML text nodes
2. Legacy form mode  — Replace known example values (e.g. '2025.00.00', '00월')
                       with real activity data, even when no placeholder markers exist
3. Mixed mode        — Both placeholder and legacy replacements applied

HWPX is a ZIP archive containing XML files.
This service:
  - Detects which mode to use from the template content
  - Builds a rich activity context (title, date, location, participants, body, …)
  - Processes all Contents/section*.xml (+ header/footer) files
  - Returns a new HWPX written to output_path
  - Provides extract_hwpx_text() for post-generation validation
"""
from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID
from xml.sax.saxutils import escape as xml_escape

# ── Regex helpers ─────────────────────────────────────────────────────────────

# Any namespace-prefixed text element: <ns:t>...</ns:t>
_TEXT_EL_RE = re.compile(r'<(?:\w+:)?t(?:\s[^>]*)?>([^<]*)</(?:\w+:)?t>')

# Placeholder pattern: {{key}}
_PLACEHOLDER_RE = re.compile(r"\{\{([^}]+)\}\}")

# Legacy pattern signatures that tell us this is a legacy-form template
_LEGACY_SIGNATURES = re.compile(r'00월|20\d{2}\.00\.00|참여인원\s*총\s*0+명|이하\s*생략')

# Known XML content-bearing extensions inside HWPX
_XML_EXTS = {".xml", ".hml", ".hml2", ".hpf"}

# Section XML glob patterns (the main document body)
_SECTION_PATTERNS = ("Contents/section", "Contents/Section")


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class HwpxContext:
    """All data needed to generate an HWPX from a template."""
    activity_title: str = ""
    activity_month: str = ""   # "06"
    activity_date: str = ""    # "2026.06.03"
    activity_location: str = ""
    activity_category: str = ""
    report_body: str = ""
    participant_count: int = 0
    participant_list: list[dict] = field(default_factory=list)
    club_name: str = ""
    representative_name: str = ""
    expense_summary: str = ""
    evidence_summary: str = ""
    feedback_summary: str = ""


@dataclass
class FieldMapping:
    source: str
    target: str
    field: str


@dataclass
class HwpxGenerationResult:
    output_path: str
    mode: str                        # "placeholder" | "legacy_form" | "mixed"
    replaced_count: int
    participant_count: int
    warnings: list[str]
    mappings: list[dict]             # [{source, target, field}, ...]
    mapped_fields: dict[str, str]    # back-compat: field → value
    missing_fields: list[str]


# ── Context builder ───────────────────────────────────────────────────────────

def build_generation_context(
    db: Any,
    activity_id: str | UUID,
    overrides: dict[str, str] | None = None,
) -> HwpxContext:
    """Build a rich HwpxContext from DB data for the given activity."""
    from sqlalchemy import select

    from app.core.config import settings
    from app.models.activity import ActivityCategory, ActivityParticipant, ActivityReport
    from app.models.member import Member

    aid = UUID(str(activity_id))
    report = db.get(ActivityReport, aid)
    if report is None:
        return HwpxContext()

    # Category
    category_name = ""
    if report.category_id:
        cat = db.get(ActivityCategory, report.category_id)
        category_name = cat.name if cat else ""

    # Report body — priority order per spec
    body = (
        report.final_content
        or report.generated_content
        or report.input_text
        or ""
    )

    # Activity date → "YYYY.MM.DD" for legacy templates
    activity_date_str = ""
    activity_month_str = ""
    if report.activity_date:
        d = report.activity_date
        activity_date_str = f"{d.year}.{d.month:02d}.{d.day:02d}"
        activity_month_str = f"{d.month:02d}"

    # Participants — joined with Member info
    participants_raw = list(db.scalars(
        select(ActivityParticipant)
        .where(ActivityParticipant.activity_report_id == aid)
    ))
    participant_list: list[dict] = []
    for p in participants_raw:
        m = db.get(Member, p.member_id)
        if m:
            participant_list.append({
                "name": m.name or "",
                "department": m.department or "",
                "student_id": m.student_id or "",
                "note": "",
            })

    # Sort by student_id, then name
    participant_list.sort(key=lambda x: (x["student_id"], x["name"]))

    club_name = getattr(settings, "CLUB_NAME", "ClubAgent")
    # Representative name — try AppSetting if available, else fallback
    representative_name = ""
    try:
        from app.models.setting import AppSetting
        setting = db.scalar(
            select(AppSetting).where(AppSetting.key == "representative_name")
        )
        if setting:
            representative_name = setting.value or ""
    except Exception:
        pass

    ctx = HwpxContext(
        activity_title=report.title or "",
        activity_month=activity_month_str,
        activity_date=activity_date_str,
        activity_location=report.location or "",
        activity_category=category_name,
        report_body=body,
        participant_count=len(participant_list),
        participant_list=participant_list,
        club_name=club_name,
        representative_name=representative_name,
    )

    # Apply user overrides
    if overrides:
        for key, val in overrides.items():
            if key in ("content", "활동내용", "report_body", "보고서본문"):
                ctx.report_body = val
            elif key in ("title", "활동명", "activity_title"):
                ctx.activity_title = val
            elif key in ("location", "활동장소", "activity_location"):
                ctx.activity_location = val

    return ctx


# ── Mode detection ─────────────────────────────────────────────────────────────

def detect_template_mode(template_path: Path) -> str:
    """Return 'placeholder', 'legacy_form', or 'mixed' based on template content."""
    try:
        text = extract_hwpx_text(template_path)
    except Exception:
        return "legacy_form"

    has_placeholder = bool(_PLACEHOLDER_RE.search(text))
    has_legacy = bool(_LEGACY_SIGNATURES.search(text))

    if has_placeholder and has_legacy:
        return "mixed"
    if has_placeholder:
        return "placeholder"
    return "legacy_form"


# ── Text extraction ───────────────────────────────────────────────────────────

def extract_hwpx_text(path: Path) -> str:
    """Extract all plain text from a HWPX file (strips XML tags)."""
    parts: list[str] = []
    try:
        with zipfile.ZipFile(str(path), "r") as zf:
            for name in _section_xml_names(zf):
                try:
                    raw = zf.read(name).decode("utf-8", errors="replace")
                    # Extract all text node contents
                    for m in _TEXT_EL_RE.finditer(raw):
                        t = m.group(1).strip()
                        if t:
                            parts.append(t)
                except Exception:
                    continue
    except Exception:
        pass
    return "\n".join(parts)


def _section_xml_names(zf: zipfile.ZipFile) -> list[str]:
    """Return names of XML files to process inside the HWPX zip."""
    result = []
    for name in zf.namelist():
        low = name.lower()
        ext = Path(name).suffix.lower()
        if ext not in _XML_EXTS:
            continue
        # Prioritise Contents/section*.xml, also include header/footer
        is_section = any(low.startswith(p.lower()) for p in _SECTION_PATTERNS)
        is_header = "header" in low
        is_footer = "footer" in low
        if is_section or is_header or is_footer:
            result.append(name)
    # Fallback: include all XML if nothing matched
    if not result:
        result = [n for n in zf.namelist() if Path(n).suffix.lower() in _XML_EXTS]
    return result


# ── Preview builder ───────────────────────────────────────────────────────────

def build_preview_mappings(
    template_path: Path,
    ctx: HwpxContext,
) -> tuple[str, list[dict], list[str]]:
    """Return (mode, mappings, warnings) for the preview API.

    Mappings are [{source, target, field}, ...] showing what will be replaced.
    """
    mode = detect_template_mode(template_path)
    template_text = ""
    try:
        template_text = extract_hwpx_text(template_path)
    except Exception:
        pass

    mappings: list[dict] = []
    warnings: list[str] = []

    if mode in ("placeholder", "mixed"):
        # List placeholders found in template and their resolved values
        for m in _PLACEHOLDER_RE.finditer(template_text):
            key = m.group(1).strip()
            val = _resolve_placeholder(key, ctx)
            if val:
                mappings.append({"source": "{{" + key + "}}", "target": val, "field": key})
            else:
                warnings.append(f"placeholder {{{{ {key} }}}} 에 대응하는 값이 없습니다.")

    if mode in ("legacy_form", "mixed"):
        # Show expected legacy replacements
        if ctx.activity_month:
            mappings.append({"source": "00월", "target": ctx.activity_month + "월", "field": "activity_month"})
        if ctx.activity_date:
            mappings.append({"source": "20xx.00.00", "target": ctx.activity_date, "field": "activity_date"})
        if ctx.activity_location:
            mappings.append({"source": "활동 장소 예시값", "target": ctx.activity_location, "field": "activity_location"})
        if ctx.activity_category:
            mappings.append({"source": "활동 분류 예시값", "target": ctx.activity_category, "field": "activity_category"})

        if ctx.report_body:
            original_len = len(ctx.report_body)
            truncated = _truncate_body_for_form(ctx.report_body, max_sentences=4)
            body_preview = truncated[:60] + "..." if len(truncated) > 60 else truncated
            mappings.append({"source": "활동 내용 예시문", "target": body_preview, "field": "report_body"})
            if original_len > 200 or original_len != len(truncated):
                warnings.append("활동 내용이 길어 제출 양식용으로 요약됩니다.")
        else:
            warnings.append("보고서 본문이 비어 있습니다. 그래도 생성하시겠습니까?")

        if ctx.participant_count > 0:
            mappings.append({
                "source": "참여인원 총 00명",
                "target": f"참여인원 총 {ctx.participant_count}명",
                "field": "participant_count",
            })
            mappings.append({
                "source": "참여자 명단",
                "target": f"{ctx.participant_count}명 (이름/학과/학번/서명/비고 표 행 삽입)",
                "field": "participant_method",
            })
            warnings.append(f"참여자 {ctx.participant_count}명이 표에 삽입됩니다.")
        else:
            warnings.append("참여자가 없습니다. 참여자 명단 없이 생성됩니다.")

    return mode, mappings, warnings


def _resolve_placeholder(key: str, ctx: HwpxContext) -> str:
    """Resolve a single placeholder key to a string value."""
    mapping = {
        "활동명": ctx.activity_title,
        "activity_title": ctx.activity_title,
        "활동일": ctx.activity_date,
        "activity_date": ctx.activity_date,
        "활동장소": ctx.activity_location,
        "location": ctx.activity_location,
        "활동분류": ctx.activity_category,
        "category": ctx.activity_category,
        "활동내용": ctx.report_body,
        "보고서본문": ctx.report_body,
        "content": ctx.report_body,
        "참여자수": str(ctx.participant_count),
        "participant_count": str(ctx.participant_count),
        "동아리명": ctx.club_name,
        "club_name": ctx.club_name,
        "대표자": ctx.representative_name,
        "representative_name": ctx.representative_name,
        "활동월": ctx.activity_month,
        "activity_month": ctx.activity_month,
    }
    return mapping.get(key, "")


# ── Main generation entry point ───────────────────────────────────────────────

def generate_hwpx(
    template_path: Path,
    output_path: Path,
    ctx: HwpxContext,
    mode: str | None = None,
) -> HwpxGenerationResult:
    """Generate a new HWPX by applying replacements to the template.

    Never modifies the original template.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if mode is None:
        mode = detect_template_mode(template_path)

    adapter = OuiParfumActivityReportHwpxAdapter.from_template(template_path)

    total_replaced = 0
    all_mappings: list[dict] = []
    all_warnings: list[str] = []
    mapped_fields: dict[str, str] = {}
    missing_fields: list[str] = []

    with zipfile.ZipFile(str(template_path), "r") as src_zf:
        with zipfile.ZipFile(str(output_path), "w", zipfile.ZIP_DEFLATED) as dst_zf:
            section_names = _section_xml_names(src_zf)

            for item in src_zf.infolist():
                raw = src_zf.read(item.filename)

                if item.filename in section_names:
                    try:
                        text = raw.decode("utf-8", errors="replace")
                        text, n, m, w = _process_xml(
                            text,
                            ctx,
                            mode,
                            mapped_fields,
                            missing_fields,
                            adapter=adapter,
                        )
                        total_replaced += n
                        all_mappings.extend(m)
                        all_warnings.extend(w)
                        raw = text.encode("utf-8")
                    except Exception as exc:
                        all_warnings.append(f"XML 처리 오류 ({item.filename}): {exc}")

                dst_zf.writestr(item, raw)

    # Dedup mappings
    seen_fields = set()
    deduped = []
    for m in all_mappings:
        k = m.get("field", m.get("source"))
        if k not in seen_fields:
            deduped.append(m)
            seen_fields.add(k)

    # Post-generation validation
    if output_path.exists():
        extracted = extract_hwpx_text(output_path)
        _validate_generation(extracted, ctx, all_warnings)

    return HwpxGenerationResult(
        output_path=str(output_path),
        mode=mode,
        replaced_count=total_replaced,
        participant_count=ctx.participant_count,
        warnings=list(dict.fromkeys(all_warnings)),  # dedup
        mappings=deduped,
        mapped_fields=mapped_fields,
        missing_fields=missing_fields,
    )


_TEMPLATE_EXAMPLE_PATTERNS = re.compile(
    r'2025\.00\.00|종합관\s*앞|참여인원\s*총\s*00명|동아리\s*홍보전에\s*참여하여|이하\s*생략'
)


def _validate_generation(text: str, ctx: HwpxContext, warnings: list[str]) -> None:
    """Add warnings if key content was not successfully inserted or examples remain."""
    if ctx.activity_date and ctx.activity_date not in text:
        warnings.append(f"활동 일시({ctx.activity_date})가 생성 문서에서 확인되지 않았습니다.")
    if ctx.activity_location and ctx.activity_location not in text:
        warnings.append(f"활동 장소({ctx.activity_location})가 생성 문서에서 확인되지 않았습니다.")
    if ctx.participant_count > 0 and str(ctx.participant_count) not in text:
        warnings.append(f"참여인원 수({ctx.participant_count}명)가 생성 문서에서 확인되지 않았습니다.")
    if ctx.report_body:
        truncated = _truncate_body_for_form(ctx.report_body, max_sentences=4)
        body_lines = [line.strip() for line in re.split(r'\r?\n+', truncated) if line.strip()]
        snippets = [line[:20] for line in body_lines if len(line) >= 4]
        if snippets and not any(snippet in text for snippet in snippets):
            warnings.append("보고서 본문이 생성 문서에서 확인되지 않았습니다.")
    # Check for remaining template example values
    m = _TEMPLATE_EXAMPLE_PATTERNS.search(text)
    if m:
        warnings.append(f"템플릿 예시값이 남아 있습니다: '{m.group(0)}'")
    # Check for body duplication: count occurrences of a key snippet
    if ctx.report_body:
        truncated = _truncate_body_for_form(ctx.report_body, max_sentences=4)
        snippet = truncated[:20]
        if snippet and len(snippet) >= 4 and text.count(snippet) > 1:
            warnings.append("활동 내용이 문서에 중복 삽입된 것으로 보입니다.")


# ── Oui Parfum real-template adapter ──────────────────────────────────────────

class OuiParfumActivityReportHwpxAdapter:
    """Adapter for the real Oui Parfum activity report HWPX template."""

    SIGNATURES = ("동아리 활동 내역서", "참여 인원 명단", "참여인원 총 00명")

    @classmethod
    def from_template(cls, template_path: Path) -> "OuiParfumActivityReportHwpxAdapter | None":
        if "Oui Parfum" in template_path.name:
            return cls()
        try:
            text = extract_hwpx_text(template_path)
        except Exception:
            text = ""
        if all(sig in text for sig in cls.SIGNATURES):
            return cls()
        return None

    def apply(self, xml_text: str, ctx: HwpxContext) -> tuple[str, int, list[dict], list[str]]:
        count = 0
        mappings: list[dict] = []
        warnings: list[str] = []

        xml_text, n, m = self._replace_simple_fields(xml_text, ctx)
        count += n
        mappings.extend(m)

        if ctx.report_body:
            lines = _split_report_body(ctx.report_body)
            body_scope = "활동 내용" in xml_text
            xml_text, n, old = self._replace_activity_body(xml_text, lines)
            if n:
                count += n
                mappings.append({
                    "source": (old[:50] + "...") if len(old) > 50 else (old or "활동 내용 예시문"),
                    "target": lines[0] if lines else "",
                    "field": "report_body",
                })
            elif body_scope:
                warnings.append("Oui Parfum 활동 내용 입력 칸을 찾지 못했습니다.")

        if ctx.participant_list:
            participant_scope = (
                "참여 인원 명단" in xml_text
                or "이하 생략" in xml_text
                or all(label in xml_text for label in ("이름", "학과", "학번", "서명", "비고"))
            )
            xml_text, n = self._replace_participant_table(xml_text, ctx.participant_list)
            if n:
                count += n
                mappings.append({
                    "source": "참여 인원 명단 표",
                    "target": f"{len(ctx.participant_list)}명 표 행 삽입",
                    "field": "participants",
                })
            elif participant_scope:
                warnings.append("Oui Parfum 참여자 명단 표를 찾지 못했습니다.")

        return xml_text, count, mappings, warnings

    def _replace_simple_fields(self, xml_text: str, ctx: HwpxContext) -> tuple[str, int, list[dict]]:
        count = 0
        mappings: list[dict] = []

        if ctx.activity_month and "00월" in xml_text:
            target = f"{ctx.activity_month}월"
            xml_text = xml_text.replace("00월", xml_escape(target), 1)
            count += 1
            mappings.append({"source": "00월", "target": target, "field": "activity_month"})

        if ctx.activity_date:
            xml_text, n = re.subn(r'20\d{2}\.0{1,2}\.0{1,2}', xml_escape(ctx.activity_date), xml_text)
            if n:
                count += 1
                mappings.append({"source": "2025.00.00", "target": ctx.activity_date, "field": "activity_date"})

        if ctx.participant_count >= 0:
            target = f"참여인원 총 {ctx.participant_count}명"
            xml_text, n = re.subn(r'참여인원\s*총\s*0+명', xml_escape(target), xml_text)
            if n:
                count += 1
                mappings.append({"source": "참여인원 총 00명", "target": target, "field": "participant_count"})

        if ctx.activity_location:
            xml_text, n, old = _replace_table_value_in_same_row(xml_text, "활동 장소", [ctx.activity_location])
            if n:
                count += 1
                mappings.append({"source": old or "활동 장소 예시값", "target": ctx.activity_location, "field": "activity_location"})

        if ctx.activity_category:
            xml_text, n, old = _replace_table_value_in_same_row(xml_text, "활동 분류", [ctx.activity_category])
            if n:
                count += 1
                mappings.append({"source": old or "활동 분류 예시값", "target": ctx.activity_category, "field": "activity_category"})

        return xml_text, count, mappings

    def _replace_activity_body(self, xml_text: str, lines: list[str]) -> tuple[str, int, str]:
        rows = _iter_rows(xml_text)
        heading_rows = [
            i for i, row in enumerate(rows)
            if "활동 내용" in row[2] and _row_texts(row[2]) == ["활동 내용"]
        ]
        if not heading_rows:
            return xml_text, 0, ""

        # The real template has an "활동 내용" section title before the photo area,
        # then a second "활동 내용" heading with the actual body cell below it.
        heading_idx = heading_rows[-1]
        if heading_idx + 1 >= len(rows):
            return xml_text, 0, ""

        target_start, target_end, target_row = rows[heading_idx + 1]
        paras = _get_paragraphs_in_range(target_row, 0, len(target_row))
        if not paras:
            return xml_text, 0, ""

        old_text = "\n".join(_row_texts(target_row))
        template_para = target_row[paras[0][0]:paras[0][1]]
        new_paras = [_clone_paragraph_with_text(template_para, line) for line in lines]
        replace_start = target_start + paras[0][0]
        replace_end = target_start + paras[-1][1]
        new_xml = xml_text[:replace_start] + "\n".join(new_paras) + xml_text[replace_end:]
        return new_xml, len(new_paras), old_text

    def _replace_participant_table(self, xml_text: str, participants: list[dict]) -> tuple[str, int]:
        tables = _iter_tables(xml_text)
        for tbl_start, tbl_end, table_xml in tables:
            rows = _iter_rows(table_xml)
            header_idx = None
            for i, row in enumerate(rows):
                texts = _row_texts(row[2])
                if all(label in texts for label in ("이름", "학과", "학번", "서명", "비고")):
                    header_idx = i
                    break
            if header_idx is None or header_idx + 1 >= len(rows):
                continue

            end_idx = None
            for i in range(header_idx + 1, len(rows)):
                if "이하 생략" in rows[i][2]:
                    end_idx = i
                    break
            if end_idx is None:
                continue

            template_row = rows[header_idx + 1][2]
            if len(_iter_cells(template_row)) < 5:
                continue

            sorted_participants = sorted(
                participants,
                key=lambda p: (p.get("student_id") or "", p.get("name") or ""),
            )
            new_rows = [
                _fill_participant_row(
                    template_row,
                    [
                        p.get("name") or "",
                        p.get("department") or "",
                        p.get("student_id") or "",
                        "",
                        p.get("note") or "",
                    ],
                    row_addr=header_idx + 1 + offset,
                )
                for offset, p in enumerate(sorted_participants)
            ]

            replace_start = rows[header_idx + 1][0]
            replace_end = rows[end_idx][1]
            new_table = table_xml[:replace_start] + "\n".join(new_rows) + table_xml[replace_end:]
            new_row_count = len(rows) - (end_idx - header_idx) + len(new_rows)
            new_table = re.sub(r'rowCnt="\d+"', f'rowCnt="{new_row_count}"', new_table, count=1)
            new_xml = xml_text[:tbl_start] + new_table + xml_text[tbl_end:]
            return new_xml, len(new_rows)

        return xml_text, 0


def _truncate_body_for_form(body: str, max_sentences: int = 4) -> str:
    """Truncate a long activity body to fit inside a submission form cell.

    Rules:
    - Strip participant lists (lines with names/student IDs / separators)
    - Remove numbered-list items (1. 2. 3. ...)
    - Keep at most max_sentences sentences
    - Return a plain 1-2 paragraph string without bullet prefixes
    """
    if not body:
        return body

    # Remove known participant-list markers
    _PARTICIPANT_LINE_RE = re.compile(
        r'(참석자|참여자|참가자|명단|이름|학번|서명|비고|이하\s*생략)',
        re.IGNORECASE,
    )
    _NUMBERED_RE = re.compile(r'^\s*\d+[\.\)]\s+')
    _SEPARATOR_RE = re.compile(r'^[-=*\s/|]+$')

    cleaned_lines: list[str] = []
    for raw_line in re.split(r'\r?\n', body):
        line = raw_line.strip()
        if not line:
            continue
        if _PARTICIPANT_LINE_RE.search(line) and len(line) < 50:
            continue
        if _SEPARATOR_RE.match(line):
            continue
        # Strip numbered prefix but keep the sentence
        line = _NUMBERED_RE.sub('', line).strip()
        if line:
            cleaned_lines.append(line)

    # Flatten into sentences (split by Korean sentence-ending punctuation)
    full_text = ' '.join(cleaned_lines)
    sentence_splits = re.split(r'(?<=[。.!?])\s*', full_text)
    sentences: list[str] = [s.strip() for s in sentence_splits if s.strip()]

    if not sentences:
        sentences = [full_text.strip()]

    if len(sentences) <= max_sentences:
        result = ' '.join(sentences)
    else:
        result = ' '.join(sentences[:max_sentences])

    # Hard character limit for the form cell (approx 200 chars)
    if len(result) > 200:
        result = result[:197] + "..."

    return result


def _split_report_body(body: str) -> list[str]:
    """Split body into HWPX paragraph lines, each sentence as a separate paragraph.

    This ensures the HWPX form cell receives multiple paragraphs rather than
    a single long text run, preventing content overlap in the submitted document.
    """
    truncated = _truncate_body_for_form(body, max_sentences=4)
    if not truncated:
        return [body.strip()] if body.strip() else [""]

    # First try explicit newlines (user-entered line breaks)
    lines = [line.strip() for line in re.split(r'\r?\n+', truncated) if line.strip()]
    if len(lines) > 1:
        return lines

    # No newlines: split into sentences so each becomes its own paragraph
    sentences = [s.strip() for s in re.split(r'(?<=[.!?。])\s+', truncated) if s.strip()]
    if len(sentences) > 1:
        return sentences

    # Single sentence or no boundary — return as-is
    return [truncated.strip()]


def _iter_tables(xml_text: str) -> list[tuple[int, int, str]]:
    result: list[tuple[int, int, str]] = []
    for m in re.finditer(r'<hp:tbl\b', xml_text):
        end = xml_text.find("</hp:tbl>", m.end())
        if end == -1:
            continue
        end += len("</hp:tbl>")
        result.append((m.start(), end, xml_text[m.start():end]))
    return result


def _iter_rows(xml_text: str) -> list[tuple[int, int, str]]:
    return [(m.start(), m.end(), m.group(0)) for m in re.finditer(r'<hp:tr>.*?</hp:tr>', xml_text, re.S)]


def _iter_cells(row_xml: str) -> list[tuple[int, int, str]]:
    return [(m.start(), m.end(), m.group(0)) for m in re.finditer(r'<hp:tc\b.*?</hp:tc>', row_xml, re.S)]


def _row_texts(row_xml: str) -> list[str]:
    return [m.group(1).strip() for m in _TEXT_EL_RE.finditer(row_xml) if m.group(1).strip()]


def _replace_table_value_in_same_row(xml_text: str, label: str, replacement_lines: list[str]) -> tuple[str, int, str]:
    for row_start, _row_end, row_xml in _iter_rows(xml_text):
        if label not in row_xml:
            continue
        cells = _iter_cells(row_xml)
        for idx, (_cell_start, cell_end, cell_xml) in enumerate(cells):
            if label not in cell_xml or idx + 1 >= len(cells):
                continue
            next_start, next_end, next_xml = cells[idx + 1]
            paras = _get_paragraphs_in_range(next_xml, 0, len(next_xml))
            if not paras:
                continue
            old_text = "\n".join(_row_texts(next_xml))
            template_para = next_xml[paras[0][0]:paras[0][1]]
            new_paras = [_clone_paragraph_with_text(template_para, line) for line in replacement_lines]
            new_cell = next_xml[:paras[0][0]] + "\n".join(new_paras) + next_xml[paras[-1][1]:]
            abs_start = row_start + next_start
            abs_end = row_start + next_end
            return xml_text[:abs_start] + new_cell + xml_text[abs_end:], len(new_paras), old_text
    return xml_text, 0, ""


def _fill_participant_row(template_row: str, values: list[str], row_addr: int) -> str:
    cells = _iter_cells(template_row)
    if len(cells) < 5:
        return template_row

    pieces: list[str] = []
    cursor = 0
    for idx, (start, end, cell_xml) in enumerate(cells):
        value = values[idx] if idx < len(values) else ""
        new_cell = _set_cell_text(cell_xml, value)
        new_cell = re.sub(r'colAddr="\d+"', f'colAddr="{idx}"', new_cell, count=1)
        new_cell = re.sub(r'rowAddr="\d+"', f'rowAddr="{row_addr}"', new_cell, count=1)
        new_cell = re.sub(r'colSpan="\d+"', 'colSpan="1"', new_cell, count=1)
        pieces.append(template_row[cursor:start])
        pieces.append(new_cell)
        cursor = end
    pieces.append(template_row[cursor:])
    return "".join(pieces)


def _set_cell_text(cell_xml: str, value: str) -> str:
    paras = _get_paragraphs_in_range(cell_xml, 0, len(cell_xml))
    if not paras:
        return cell_xml
    template_para = cell_xml[paras[0][0]:paras[0][1]]
    new_para = _clone_paragraph_with_text(template_para, value)
    # Keep one paragraph per participant cell so note/header leftovers cannot leak.
    return cell_xml[:paras[0][0]] + new_para + cell_xml[paras[-1][1]:]


# ── XML processing core ────────────────────────────────────────────────────────

def _process_xml(
    xml_text: str,
    ctx: HwpxContext,
    mode: str,
    mapped_fields: dict[str, str],
    missing_fields: list[str],
    adapter: "OuiParfumActivityReportHwpxAdapter | None" = None,
) -> tuple[str, int, list[dict], list[str]]:
    """Apply all replacements to a single XML file content."""
    count = 0
    mappings: list[dict] = []
    warnings: list[str] = []

    if mode in ("placeholder", "mixed"):
        xml_text, n, m = _apply_placeholder_mode(xml_text, ctx, mapped_fields, missing_fields)
        count += n
        mappings.extend(m)

    if adapter is not None:
        xml_text, n, m, w = adapter.apply(xml_text, ctx)
        count += n
        mappings.extend(m)
        warnings.extend(w)
    elif mode in ("legacy_form", "mixed"):
        xml_text, n, m = _apply_legacy_mode(xml_text, ctx)
        count += n
        mappings.extend(m)

    return xml_text, count, mappings, warnings


# ── Placeholder mode ──────────────────────────────────────────────────────────

def _apply_placeholder_mode(
    xml_text: str,
    ctx: HwpxContext,
    mapped_fields: dict[str, str],
    missing_fields: list[str],
) -> tuple[str, int, list[dict]]:
    """Replace {{key}} placeholders with context values."""
    count = 0
    mappings: list[dict] = []

    def _replacer(match: re.Match) -> str:
        nonlocal count
        key = match.group(1).strip()
        val = _resolve_placeholder(key, ctx)
        if val:
            mapped_fields[key] = val
            count += 1
            mappings.append({"source": "{{" + key + "}}", "target": val, "field": key})
            return xml_escape(val)
        if key not in missing_fields:
            missing_fields.append(key)
        return xml_escape("(미입력)")

    result = _PLACEHOLDER_RE.sub(_replacer, xml_text)
    return result, count, mappings


# ── Legacy form mode ──────────────────────────────────────────────────────────

def _apply_legacy_mode(xml_text: str, ctx: HwpxContext) -> tuple[str, int, list[dict]]:
    """Apply legacy form replacements: date, month, count, headings, participants."""
    count = 0
    mappings: list[dict] = []

    # ── 1. Month: "00월" → "{month}월" ───────────────────────────────────────
    if ctx.activity_month:
        target = ctx.activity_month + "월"
        n = xml_text.count("00월")
        if n:
            xml_text = xml_text.replace("00월", xml_escape(target))
            count += 1
            mappings.append({"source": "00월", "target": target, "field": "activity_month"})

    # ── 2. Date: "2025.00.00" / "20XX.00.00" → "YYYY.MM.DD" ─────────────────
    if ctx.activity_date:
        date_str = ctx.activity_date  # already "YYYY.MM.DD"
        new_text, n = re.subn(r'20\d{2}\.0{1,2}\.0{1,2}', xml_escape(date_str), xml_text)
        if n:
            count += 1
            mappings.append({"source": "20xx.00.00", "target": date_str, "field": "activity_date"})
        xml_text = new_text

    # ── 3. Participant count: "참여인원 총 00명" → actual ─────────────────────
    if ctx.participant_count >= 0:
        target = f"참여인원 총 {ctx.participant_count}명"
        new_text, n = re.subn(
            r'참여인원\s*총\s*0+명',
            xml_escape(target),
            xml_text,
        )
        if n:
            count += 1
            mappings.append({"source": "참여인원 총 00명", "target": target, "field": "participant_count"})
        xml_text = new_text

    # ── 4. Location: replace paragraph after "활동 장소" heading ────────────────
    if ctx.activity_location:
        new_text, n, old = _replace_paragraph_after_heading(
            xml_text, "활동 장소", [ctx.activity_location]
        )
        if n:
            count += 1
            mappings.append({"source": old or "활동 장소 예시값", "target": ctx.activity_location, "field": "activity_location"})
        xml_text = new_text

    # ── 5. Category: replace paragraph after "활동 분류" heading ─────────────
    if ctx.activity_category:
        new_text, n, old = _replace_paragraph_after_heading(
            xml_text, "활동 분류", [ctx.activity_category]
        )
        if n:
            count += 1
            mappings.append({"source": old or "활동 분류 예시값", "target": ctx.activity_category, "field": "activity_category"})
        xml_text = new_text

    # ── 6. Activity body: replace paragraphs after "활동 내용" heading ─────────
    if ctx.report_body:
        # Split into lines so each becomes its own paragraph in HWPX
        body_lines = [l for l in ctx.report_body.split("\n") if l.strip()]
        if not body_lines:
            body_lines = [ctx.report_body]
        new_text, n, old = _replace_paragraph_after_heading(xml_text, "활동 내용", body_lines)
        if n:
            count += 1
            preview = ctx.report_body[:50] + ("..." if len(ctx.report_body) > 50 else "")
            mappings.append({"source": (old[:50] + "...") if len(old) > 50 else (old or "활동 내용 예시문"), "target": preview, "field": "report_body"})
        xml_text = new_text

    # ── 7. Participant roster: replace "이하 생략" ────────────────────────────
    if ctx.participant_list:
        new_text, n = _replace_participant_roster(xml_text, ctx.participant_list)
        if n:
            count += n
            mappings.append({"source": "이하 생략", "target": f"{len(ctx.participant_list)}명 명단 삽입", "field": "participants"})
        xml_text = new_text

    return xml_text, count, mappings


def _replace_text_after_heading(
    xml_text: str,
    heading: str,
    replacement: str,
) -> tuple[str, int, str]:
    """Find the heading text inside an XML text element, then replace the NEXT
    non-empty text element with replacement.  (Single-line fallback.)

    Returns (new_xml, replaced_count, old_text_found).
    """
    matches = list(_TEXT_EL_RE.finditer(xml_text))

    heading_idx: int | None = None
    for i, m in enumerate(matches):
        if heading in m.group(1):
            heading_idx = i
            break

    if heading_idx is None:
        return xml_text, 0, ""

    for i in range(heading_idx + 1, len(matches)):
        m = matches[i]
        text = m.group(1).strip()
        if text:
            old_text = text
            new_xml = (
                xml_text[: m.start(1)]
                + xml_escape(replacement)
                + xml_text[m.end(1) :]
            )
            return new_xml, 1, old_text

    return xml_text, 0, ""


# ── Paragraph-level helpers ───────────────────────────────────────────────────

# Match opening paragraph-like tags: <hp:p>, <p>, <hml:para> etc. (not self-closing)
_PARA_OPEN_RE = re.compile(r'<((?:\w+:)?p)\b[^>]*?(?<!/)>', re.IGNORECASE)

# Match table-cell and table-row elements (HWPX: <hp:tc>, <hp:tr>)
_TC_OPEN_RE = re.compile(r'<((?:\w+:)?tc)\b[^>]*?(?<!/)>', re.IGNORECASE)
_TR_OPEN_RE = re.compile(r'<((?:\w+:)?tr)\b[^>]*?(?<!/)>', re.IGNORECASE)


def _find_innermost(xml_text: str, pos: int, open_re: re.Pattern) -> tuple[int, int, str] | None:
    """Find the innermost element matched by `open_re` that contains `pos`."""
    best: tuple[int, int, str] | None = None

    for m in open_re.finditer(xml_text):
        if m.start() >= pos:
            break

        tag_name = m.group(1)
        close_tag = f"</{tag_name}>"
        close_pos = xml_text.find(close_tag, m.end())
        if close_pos == -1:
            continue

        elem_end = close_pos + len(close_tag)
        if elem_end > pos:
            if best is None or m.start() > best[0]:
                best = (m.start(), elem_end, tag_name)

    return best


def _find_enclosing_paragraph(xml_text: str, pos: int) -> tuple[int, int, str] | None:
    return _find_innermost(xml_text, pos, _PARA_OPEN_RE)


def _find_enclosing_table_cell(xml_text: str, pos: int) -> tuple[int, int, str] | None:
    return _find_innermost(xml_text, pos, _TC_OPEN_RE)


def _find_enclosing_table_row(xml_text: str, pos: int) -> tuple[int, int, str] | None:
    return _find_innermost(xml_text, pos, _TR_OPEN_RE)


def _find_next_element(
    xml_text: str, after_pos: int, open_re: re.Pattern
) -> tuple[int, int, str] | None:
    """Find the first element matched by `open_re` starting at or after `after_pos`."""
    m = open_re.search(xml_text, after_pos)
    if not m:
        return None
    tag_name = m.group(1)
    close_tag = f"</{tag_name}>"
    close_pos = xml_text.find(close_tag, m.end())
    if close_pos == -1:
        return None
    return m.start(), close_pos + len(close_tag), tag_name


def _get_paragraphs_in_range(xml_text: str, start: int, end: int) -> list[tuple[int, int]]:
    """Return (start, end) positions of every paragraph element inside [start, end)."""
    result = []
    for m in _PARA_OPEN_RE.finditer(xml_text, start, end):
        tag_name = m.group(1)
        close_tag = f"</{tag_name}>"
        close_pos = xml_text.find(close_tag, m.end(), end)
        if close_pos == -1:
            continue
        result.append((m.start(), close_pos + len(close_tag)))
    return result


def _clone_paragraph_with_text(template_para: str, new_text: str) -> str:
    """Return a copy of `template_para` with ALL text element contents replaced.

    The first `<ns:t>` gets `new_text`; the rest are emptied.
    Preserves paragraph formatting (pPr, rPr, fonts, etc.).
    """
    text_matches = list(_TEXT_EL_RE.finditer(template_para))
    if not text_matches:
        return _insert_text_into_empty_paragraph(template_para, new_text)

    result = template_para
    for i in range(len(text_matches) - 1, -1, -1):
        m = text_matches[i]
        replacement_content = xml_escape(new_text) if i == 0 else ""
        result = result[: m.start(1)] + replacement_content + result[m.end(1):]

    return result


def _insert_text_into_empty_paragraph(template_para: str, new_text: str) -> str:
    """Insert text into a paragraph that has an empty self-closing run."""
    escaped = xml_escape(new_text)

    run_match = re.search(r'<((?:\w+:)?run)\b([^>]*)/>', template_para)
    if run_match:
        run_tag = run_match.group(1)
        prefix = run_tag.split(":", 1)[0] if ":" in run_tag else ""
        t_tag = f"{prefix}:t" if prefix else "t"
        run_xml = f"<{run_tag}{run_match.group(2)}><{t_tag}>{escaped}</{t_tag}></{run_tag}>"
        return template_para[:run_match.start()] + run_xml + template_para[run_match.end():]

    para_match = re.search(r'<((?:\w+:)?p)\b[^>]*>', template_para)
    if para_match:
        para_tag = para_match.group(1)
        prefix = para_tag.split(":", 1)[0] if ":" in para_tag else ""
        run_tag = f"{prefix}:run" if prefix else "run"
        t_tag = f"{prefix}:t" if prefix else "t"
        insert = f'<{run_tag} charPrIDRef="0"><{t_tag}>{escaped}</{t_tag}></{run_tag}>'
        close = f"</{para_tag}>"
        close_pos = template_para.rfind(close)
        if close_pos != -1:
            return template_para[:close_pos] + insert + template_para[close_pos:]

    return template_para


def _replace_paragraph_after_heading(
    xml_text: str,
    heading: str,
    replacement_lines: list[str],
) -> tuple[str, int, str]:
    """Replace content after a heading with one cloned paragraph per line.

    Priority:
    1. TABLE CELL NEIGHBOR — heading is in a <hp:tc>; find the NEXT sibling
       cell and replace ALL its paragraphs (covers HWPX form table structure).
    2. NEXT PARAGRAPH AFTER HEADING — standalone heading paragraph; replace
       the first following non-empty paragraph with cloned versions.
    3. TEXT-NODE FALLBACK — no paragraph structure found; replace first line.

    In case multiple occurrences of `heading` exist the one inside a table
    cell is tried first, as that is the actual form field.

    Returns (new_xml, paragraph_count_inserted, old_text_found).
    """
    matches = list(_TEXT_EL_RE.finditer(xml_text))

    heading_occurrences = [i for i, m in enumerate(matches) if heading in m.group(1)]
    if not heading_occurrences:
        return xml_text, 0, ""

    # Prefer occurrences inside a table cell (form field) over standalone ones
    def _in_table_cell(idx: int) -> bool:
        return _find_enclosing_table_cell(xml_text, matches[idx].start()) is not None

    heading_occurrences.sort(key=lambda i: (0 if _in_table_cell(i) else 1))

    for heading_idx in heading_occurrences:
        heading_match = matches[heading_idx]

        # ── Strategy 1: table cell neighbor ──────────────────────────────────
        tc_info = _find_enclosing_table_cell(xml_text, heading_match.start())
        if tc_info is not None:
            _tc_start, tc_end, _ = tc_info
            next_tc = _find_next_element(xml_text, tc_end, _TC_OPEN_RE)
            if next_tc is not None:
                ntc_start, ntc_end, _ = next_tc
                paras = _get_paragraphs_in_range(xml_text, ntc_start, ntc_end)
                if paras:
                    template_para = xml_text[paras[0][0]: paras[0][1]]
                    old_text = "".join(
                        tm.group(1) for tm in _TEXT_EL_RE.finditer(template_para)
                    )
                    replace_start = paras[0][0]
                    replace_end = paras[-1][1]
                    new_paras = [
                        _clone_paragraph_with_text(template_para, line)
                        for line in replacement_lines if line.strip()
                    ] or [_clone_paragraph_with_text(template_para, "")]
                    new_xml = (
                        xml_text[:replace_start]
                        + "\n".join(new_paras)
                        + xml_text[replace_end:]
                    )
                    return new_xml, len(new_paras), old_text

        # ── Strategy 2: next paragraph after heading ──────────────────────────
        for i in range(heading_idx + 1, len(matches)):
            m = matches[i]
            text = m.group(1).strip()
            if not text:
                continue

            old_text = text
            para_info = _find_enclosing_paragraph(xml_text, m.start())

            if para_info is None:
                first = replacement_lines[0] if replacement_lines else ""
                new_xml = xml_text[:m.start(1)] + xml_escape(first) + xml_text[m.end(1):]
                return new_xml, 1, old_text

            para_start, para_end, _ = para_info
            template_para = xml_text[para_start:para_end]
            new_paras = [
                _clone_paragraph_with_text(template_para, line)
                for line in replacement_lines if line.strip()
            ] or [_clone_paragraph_with_text(template_para, "")]
            new_xml = xml_text[:para_start] + "\n".join(new_paras) + xml_text[para_end:]
            return new_xml, len(new_paras), old_text

    return xml_text, 0, ""


def _replace_participant_roster(
    xml_text: str,
    participants: list[dict],
) -> tuple[str, int]:
    """Replace '이하 생략' with per-participant entries.

    Priority:
    1. TABLE ROW CLONE (Method B): clone the <hp:tr> that contains '이하 생략',
       one row per participant.
    2. PARAGRAPH CLONE (Method A): clone the <hp:p>, one per participant.
    3. TEXT FALLBACK: newline-separated text (no '|' join ever).
    """
    if "이하 생략" not in xml_text:
        return xml_text, 0

    sorted_p = sorted(participants, key=lambda x: (x.get("student_id") or "", x.get("name") or ""))

    def _participant_line(p: dict) -> str:
        name = p.get("name") or ""
        dept = p.get("department") or ""
        sid = p.get("student_id") or ""
        return "  /  ".join(x for x in [name, dept, sid] if x)

    for m in _TEXT_EL_RE.finditer(xml_text):
        if "이하 생략" not in m.group(1):
            continue

        # ── Method B: table row clone ─────────────────────────────────────────
        tr_info = _find_enclosing_table_row(xml_text, m.start())
        if tr_info is not None:
            tr_start, tr_end, _ = tr_info
            template_row = xml_text[tr_start:tr_end]
            if len(_iter_cells(template_row)) >= 5:
                new_rows = [
                    _fill_participant_row(
                        template_row.replace("이하 생략", ""),
                        [
                            p.get("name") or "",
                            p.get("department") or "",
                            p.get("student_id") or "",
                            "",
                            p.get("note") or "",
                        ],
                        row_addr=idx + 1,
                    )
                    for idx, p in enumerate(sorted_p)
                ]
            else:
                new_rows = [
                    template_row.replace("이하 생략", xml_escape(_participant_line(p)))
                    for p in sorted_p
                ]
            if not new_rows:
                return xml_text, 0
            new_xml = xml_text[:tr_start] + "\n".join(new_rows) + xml_text[tr_end:]
            return new_xml, len(new_rows)

        # ── Method A: paragraph clone ─────────────────────────────────────────
        para_info = _find_enclosing_paragraph(xml_text, m.start())
        if para_info is not None:
            para_start, para_end, _ = para_info
            template_para = xml_text[para_start:para_end]
            new_paras = [
                _clone_paragraph_with_text(template_para, _participant_line(p))
                for p in sorted_p
            ]
            if not new_paras:
                return xml_text, 0
            new_xml = xml_text[:para_start] + "\n".join(new_paras) + xml_text[para_end:]
            return new_xml, len(new_paras)

        break  # only handle the first "이하 생략"

    # ── Text fallback (no | join) ─────────────────────────────────────────────
    lines_text = xml_escape("\n".join(_participant_line(p) for p in sorted_p))
    new_xml = xml_text.replace("이하 생략", lines_text)
    return new_xml, 1 if new_xml != xml_text else 0
