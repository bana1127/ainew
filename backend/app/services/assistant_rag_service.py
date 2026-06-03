from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RagSearchResult:
    source_type: str
    source_id: str
    title: str
    snippet: str
    target_url: str


def _text(value: Any) -> str:
    return str(value or "")


def _snippet(text: str, query: str, *, size: int = 140) -> str:
    haystack = text.strip().replace("\n", " ")
    if not haystack:
        return ""
    lower = haystack.lower()
    needle = query.lower().strip()
    idx = lower.find(needle) if needle else -1
    if idx < 0:
        return haystack[:size]
    start = max(0, idx - 40)
    end = min(len(haystack), idx + len(needle) + 80)
    return haystack[start:end]


def search_assistant_documents(db: Any, query: str, *, limit: int = 5) -> list[dict[str, Any]]:
    """Simple first-pass text search for the floating assistant.

    This deliberately stays read-only and avoids a vector dependency. It scans
    the document-like fields already present in ClubAgent and returns compact
    snippets with target URLs for the UI.
    """
    from sqlalchemy import select

    from app.models import ActivityReport, Receipt, UploadedFile
    from app.models.assistant_action import AssistantActionProposal

    q = query.strip().lower()
    words = [w for w in q.replace("?", " ").split() if len(w) >= 2]
    results: list[RagSearchResult] = []

    def score_blob(blob: str) -> int:
        lower = blob.lower()
        return sum(1 for word in words if word in lower)

    for report in db.scalars(select(ActivityReport).where(ActivityReport.deleted_at.is_(None))):
        blob = " ".join(
            [
                _text(report.title),
                _text(report.input_text),
                _text(report.generated_content),
                _text(report.final_content),
            ]
        )
        score = score_blob(blob)
        if score <= 0:
            continue
        results.append(
            RagSearchResult(
                source_type="activity_report",
                source_id=str(report.id),
                title=report.title,
                snippet=_snippet(blob, words[0] if words else query),
                target_url=f"/activities/{report.id}",
            )
        )

    for receipt in db.scalars(select(Receipt)):
        blob = " ".join(
            [
                _text(receipt.store_name),
                _text(receipt.category),
                _text(receipt.payment_method),
                _text(receipt.reason),
                _text(receipt.evidence_status),
            ]
        )
        score = score_blob(blob)
        if score <= 0:
            continue
        target = (
            f"/activities/{receipt.activity_report_id}?tab=evidence"
            if receipt.activity_report_id
            else "/receipts"
        )
        results.append(
            RagSearchResult(
                source_type="receipt",
                source_id=str(receipt.id),
                title=receipt.store_name or "영수증",
                snippet=_snippet(blob, words[0] if words else query),
                target_url=target,
            )
        )

    for uploaded in db.scalars(select(UploadedFile).where(UploadedFile.deleted_at.is_(None))):
        metadata = uploaded.preview_metadata_json or {}
        blob = " ".join(
            [
                _text(uploaded.original_filename),
                _text(uploaded.file_category),
                _text(uploaded.file_role),
                _text(metadata.get("summary")),
                _text(metadata.get("extracted_text")),
                _text(metadata.get("raw_text")),
            ]
        )
        score = score_blob(blob)
        if score <= 0:
            continue
        target = (
            f"/activities/{uploaded.activity_report_id}?tab=files"
            if uploaded.activity_report_id
            else "/references"
        )
        results.append(
            RagSearchResult(
                source_type="uploaded_file",
                source_id=str(uploaded.id),
                title=uploaded.original_filename,
                snippet=_snippet(blob, words[0] if words else query),
                target_url=target,
            )
        )

    for proposal in db.scalars(select(AssistantActionProposal)):
        blob = " ".join(
            [
                _text(proposal.action_type),
                _text(proposal.source),
                _text(proposal.payload_json),
                _text(proposal.preview_json),
                _text(proposal.status),
            ]
        )
        score = score_blob(blob)
        if score <= 0:
            continue
        target = (
            f"/activities/{proposal.activity_id}?tab=ai"
            if proposal.activity_id
            else "/assistant"
        )
        results.append(
            RagSearchResult(
                source_type="assistant_action",
                source_id=str(proposal.id),
                title=f"AI 작업 제안: {proposal.action_type}",
                snippet=_snippet(blob, words[0] if words else query),
                target_url=target,
            )
        )

    ranked = sorted(
        results,
        key=lambda item: (
            -score_blob(" ".join([item.title, item.snippet])),
            item.title,
        ),
    )
    return [item.__dict__ for item in ranked[:limit]]
