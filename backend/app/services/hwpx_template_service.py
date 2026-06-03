"""HWPX template service.

HWPX is a zip archive containing XML/HML files.
This service:
  1. Extracts {{placeholder}} fields from HWPX XML
  2. Builds activity data context
  3. Generates a new HWPX by substituting placeholders

Limitations:
  - Only supports placeholders that are wholly inside a single XML text node.
  - Placeholders split across multiple XML run/span elements are TODO.
  - HWP (binary) is NOT supported for generation.
"""
from __future__ import annotations

import io
import re
import zipfile
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID
from xml.sax.saxutils import escape as xml_escape


# ── placeholder ────────────────────────────────────────────────────────────────

_PLACEHOLDER_RE = re.compile(r"\{\{([^}]+)\}\}")

# Korean ↔ English alias mapping (both directions)
_KO_EN: dict[str, str] = {
    "활동명": "activity_title",
    "활동일": "activity_date",
    "활동장소": "location",
    "활동분류": "category",
    "활동상태": "status",
    "활동목적": "purpose",
    "활동내용": "content",
    "활동결과": "result",
    "향후계획": "next_plan",
    "참여자명단": "participants",
    "참여자수": "participant_count",
    "활동비금액": "activity_fee_amount",
    "활동비납부현황": "payment_summary",
    "영수증목록": "receipts",
    "증빙상태": "evidence_status",
    "피드백요약": "feedback_summary",
    "작성일": "generated_date",
    "동아리명": "club_name",
}
_EN_KO: dict[str, str] = {v: k for k, v in _KO_EN.items()}

XML_EXTENSIONS = {".xml", ".hml", ".hml2", ".hpf", ".hpj"}


@dataclass
class GeneratedHwpxResult:
    output_path: str
    mapped_fields: dict[str, str]
    missing_fields: list[str]
    placeholder_count: int


# ── extraction ─────────────────────────────────────────────────────────────────

def extract_hwpx_placeholders(file_path: str | Path) -> list[str]:
    """Return list of unique placeholder names (inner content of {{...}}) found in the HWPX."""
    found: set[str] = set()
    try:
        with zipfile.ZipFile(str(file_path), "r") as zf:
            for name in zf.namelist():
                if Path(name).suffix.lower() in XML_EXTENSIONS or "content" in name.lower():
                    try:
                        raw = zf.read(name).decode("utf-8", errors="replace")
                        for match in _PLACEHOLDER_RE.finditer(raw):
                            found.add(match.group(1).strip())
                    except Exception:
                        continue
    except Exception:
        pass
    return sorted(found)


# ── context builder ────────────────────────────────────────────────────────────

def build_activity_template_context(
    db: Any,  # sqlalchemy Session
    activity_id: str | UUID,
    user_overrides: dict[str, str] | None = None,
) -> dict[str, str]:
    """Build template field context from activity DB data.

    Returns a flat dict where keys are both Korean and English field names.
    user_overrides values take priority over DB-derived values.
    """
    from sqlalchemy import and_, select

    from app.core.config import settings
    from app.models.activity import ActivityParticipant, ActivityReport
    from app.models.activity_feedback import ActivityFeedback
    from app.models.payment import PaymentRecord
    from app.models.receipt import Receipt

    activity_id_uuid = UUID(str(activity_id))

    report = db.get(ActivityReport, activity_id_uuid)
    if report is None:
        return {}

    # Category
    category_name = ""
    if report.category_id:
        from app.models.activity import ActivityCategory
        cat = db.get(ActivityCategory, report.category_id)
        category_name = cat.name if cat else ""

    # Participants
    participants = list(db.scalars(
        select(ActivityParticipant)
        .where(ActivityParticipant.activity_report_id == activity_id_uuid)
    ))
    participant_names: list[str] = []
    for p in participants:
        from app.models.member import Member
        m = db.get(Member, p.member_id)
        if m:
            participant_names.append(m.name)
    participants_str = ", ".join(participant_names)

    # Activity fee
    from sqlalchemy import and_
    period_key = f"act-{str(activity_id_uuid)[:8]}"
    fee_records = list(db.scalars(
        select(PaymentRecord).where(
            and_(
                PaymentRecord.period == period_key,
                PaymentRecord.payment_type == "activity_fee",
            )
        )
    ))
    fee_amount_str = ""
    payment_summary_str = ""
    if fee_records:
        fee_amount_str = str(fee_records[0].required_amount)
        paid_count = sum(1 for r in fee_records if r.status == "paid")
        payment_summary_str = f"{paid_count}/{len(fee_records)}명 납부"

    # Receipts
    receipts = list(db.scalars(
        select(Receipt).where(Receipt.activity_report_id == activity_id_uuid)
    ))
    receipts_str = ""
    if receipts:
        lines = []
        for r in receipts:
            store = r.store_name or "(상호명 없음)"
            amt = f"{r.amount:,}" if r.amount else "0"
            lines.append(f"{store} {amt}원")
        receipts_str = "\n".join(lines)
    evidence_status_str = "확인 완료" if all(r.evidence_status == "valid" for r in receipts) and receipts else \
                          "확인 필요" if any(r.need_check for r in receipts) else \
                          ""

    # Feedback summary
    feedbacks = list(db.scalars(
        select(ActivityFeedback).where(ActivityFeedback.activity_id == activity_id_uuid)
    ))
    feedback_summary_str = f"{len(feedbacks)}건 수집됨" if feedbacks else ""

    # Report content — use priority
    content_str = (
        report.final_content
        or report.generated_content
        or report.input_text
        or ""
    )

    # Club name
    club_name = getattr(settings, "CLUB_NAME", "ClubAgent")

    ctx: dict[str, str] = {
        # Korean
        "활동명": report.title or "",
        "활동일": str(report.activity_date) if report.activity_date else "",
        "활동장소": report.location or "",
        "활동분류": category_name,
        "활동상태": _status_label(report.status),
        "활동목적": report.input_text or "",
        "활동내용": content_str,
        "활동결과": "",
        "향후계획": "",
        "참여자명단": participants_str,
        "참여자수": str(len(participants)),
        "활동비금액": fee_amount_str,
        "활동비납부현황": payment_summary_str,
        "영수증목록": receipts_str,
        "증빙상태": evidence_status_str,
        "피드백요약": feedback_summary_str,
        "작성일": datetime.now(tz=timezone.utc).strftime("%Y-%m-%d"),
        "동아리명": club_name,
        # English aliases
        "activity_title": report.title or "",
        "activity_date": str(report.activity_date) if report.activity_date else "",
        "location": report.location or "",
        "category": category_name,
        "status": _status_label(report.status),
        "purpose": report.input_text or "",
        "content": content_str,
        "result": "",
        "next_plan": "",
        "participants": participants_str,
        "participant_count": str(len(participants)),
        "activity_fee_amount": fee_amount_str,
        "payment_summary": payment_summary_str,
        "receipts": receipts_str,
        "evidence_status": evidence_status_str,
        "feedback_summary": feedback_summary_str,
        "generated_date": datetime.now(tz=timezone.utc).strftime("%Y-%m-%d"),
        "club_name": club_name,
    }

    # Merge user overrides (user-provided values take priority)
    if user_overrides:
        for key, val in user_overrides.items():
            ctx[key] = val
            # Also set the alias
            if key in _KO_EN:
                ctx[_KO_EN[key]] = val
            elif key in _EN_KO:
                ctx[_EN_KO[key]] = val

    return ctx


def _status_label(status: str) -> str:
    return {
        "planned": "예정",
        "in_progress": "진행 중",
        "done": "완료",
        "draft": "초안",
        "confirmed": "확정",
        "archived": "보관",
        "generated": "생성됨",
    }.get(status, status)


# ── generator ─────────────────────────────────────────────────────────────────

def generate_hwpx_from_template(
    template_path: str | Path,
    output_path: str | Path,
    context: dict[str, str],
) -> GeneratedHwpxResult:
    """Create a new HWPX by substituting {{placeholders}} with context values.

    Never modifies the original template.
    """
    template_path = Path(template_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    mapped_fields: dict[str, str] = {}
    missing_fields: list[str] = []
    placeholder_count = 0

    # Gather all placeholders found in template
    all_placeholders = extract_hwpx_placeholders(template_path)

    with zipfile.ZipFile(str(template_path), "r") as src_zf:
        with zipfile.ZipFile(str(output_path), "w", zipfile.ZIP_DEFLATED) as dst_zf:
            for item in src_zf.infolist():
                raw = src_zf.read(item.filename)

                if Path(item.filename).suffix.lower() in XML_EXTENSIONS or \
                   "content" in item.filename.lower():
                    try:
                        text = raw.decode("utf-8", errors="replace")
                        text, n = _substitute_placeholders(text, context, mapped_fields, missing_fields)
                        placeholder_count += n
                        raw = text.encode("utf-8")
                    except Exception:
                        pass  # copy as-is on failure

                dst_zf.writestr(item, raw)

    # Fields present in template but not in context
    for ph in all_placeholders:
        if ph not in mapped_fields and ph not in missing_fields:
            missing_fields.append(ph)

    return GeneratedHwpxResult(
        output_path=str(output_path),
        mapped_fields=mapped_fields,
        missing_fields=missing_fields,
        placeholder_count=placeholder_count,
    )


def _substitute_placeholders(
    text: str,
    context: dict[str, str],
    mapped_fields: dict[str, str],
    missing_fields: list[str],
) -> tuple[str, int]:
    """Replace all {{key}} in text with XML-escaped context values."""
    count = 0

    def _replacer(match: re.Match) -> str:
        nonlocal count
        key = match.group(1).strip()
        if key in context:
            val = xml_escape(str(context[key]))
            mapped_fields[key] = context[key]
            count += 1
            return val
        else:
            if key not in missing_fields:
                missing_fields.append(key)
            return xml_escape("미입력")

    result = _PLACEHOLDER_RE.sub(_replacer, text)
    return result, count
