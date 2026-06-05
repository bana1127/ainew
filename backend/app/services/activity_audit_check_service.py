"""Activity audit readiness check service (Task 34).

Computes a structured checklist for a given activity showing whether it is
ready for audit/submission.

Checklist items:
  1. 기본 정보 입력 — title + activity_date + location set
  2. 참여자 명단 있음 — at least one participant
  3. 활동 보고서 본문 있음 — final_content or generated_content present
  4. HWPX 생성됨 — a generated .hwpx file exists in the file vault
  5. 증빙 파일 있음 — at least one receipt linked
  6. 영수증 분석 완료 — all receipts have evidence_status in (valid, invalid) — not pending
  7. 활동비 납부 현황 생성됨 — activity_fee PaymentRecords exist
"""
from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

INACTIVE_PARTICIPANT_STATUSES = {"removed", "cancelled", "excluded", "deleted", "inactive"}
INACTIVE_ACTIVITY_FEE_STATUSES = {"cancelled", "excluded"}


@dataclass
class AuditCheckItem:
    key: str
    label: str
    done: bool
    detail: str | None = None
    count: int | None = None
    warning: str | None = None


@dataclass
class ActivityAuditCheckResult:
    activity_id: str
    activity_title: str
    items: list[AuditCheckItem] = field(default_factory=list)
    total_done: int = 0
    total_items: int = 0
    ready_for_audit: bool = False


def compute_audit_checklist(db: Session, activity_id: UUID) -> ActivityAuditCheckResult:
    """Compute a full audit checklist for the given activity."""
    from app.models.activity import ActivityParticipant, ActivityReport
    from app.models.file import UploadedFile
    from app.models.payment import PaymentRecord
    from app.models.receipt import Receipt

    report = db.get(ActivityReport, activity_id)
    if not report:
        raise ValueError(f"Activity not found: {activity_id}")

    items: list[AuditCheckItem] = []

    # 1. Basic info
    has_title = bool(report.title and report.title.strip())
    has_date = report.activity_date is not None
    has_location = bool(report.location and report.location.strip())
    basic_info_ok = has_title and has_date and has_location
    missing_fields = []
    if not has_title:
        missing_fields.append("활동명")
    if not has_date:
        missing_fields.append("활동 일자")
    if not has_location:
        missing_fields.append("활동 장소")
    items.append(AuditCheckItem(
        key="basic_info",
        label="기본 정보 입력",
        done=basic_info_ok,
        detail=f"미입력: {', '.join(missing_fields)}" if missing_fields else None,
    ))

    # 2. Participants
    participants = list(db.scalars(
        select(ActivityParticipant).where(
            and_(
                ActivityParticipant.activity_report_id == activity_id,
                (
                    ActivityParticipant.status.is_(None)
                    | ActivityParticipant.status.notin_(INACTIVE_PARTICIPANT_STATUSES)
                ),
            )
        )
    ))
    items.append(AuditCheckItem(
        key="participants",
        label="참여자 명단",
        done=len(participants) > 0,
        count=len(participants),
    ))

    # 3. Report body
    has_report = bool(report.final_content or report.generated_content)
    items.append(AuditCheckItem(
        key="report_body",
        label="활동 보고서 본문",
        done=has_report,
        detail="final_content 또는 generated_content 필요" if not has_report else None,
    ))

    # 4. HWPX generated
    hwpx_files = list(db.scalars(
        select(UploadedFile).where(
            and_(
                UploadedFile.activity_report_id == activity_id,
                UploadedFile.file_ext == "hwpx",
                UploadedFile.file_role == "generated",
                UploadedFile.deleted_at.is_(None),
            )
        )
    ))
    items.append(AuditCheckItem(
        key="hwpx_generated",
        label="HWPX 제출 문서 생성",
        done=len(hwpx_files) > 0,
        count=len(hwpx_files),
        warning="보고서 탭에서 HWPX 생성 필요" if not hwpx_files else None,
    ))

    # 5. Evidence files (receipts)
    receipts = list(db.scalars(
        select(Receipt).where(Receipt.activity_report_id == activity_id)
    ))
    items.append(AuditCheckItem(
        key="evidence_receipts",
        label="증빙 파일 (영수증)",
        done=len(receipts) > 0,
        count=len(receipts),
    ))

    # 6. Receipt analysis complete
    pending_receipts = [r for r in receipts if r.evidence_status == "pending"]
    receipts_analyzed = len(receipts) > 0 and len(pending_receipts) == 0
    items.append(AuditCheckItem(
        key="receipts_analyzed",
        label="영수증 분석 완료",
        done=receipts_analyzed,
        detail=f"분석 대기: {len(pending_receipts)}건" if pending_receipts else None,
        warning="증빙 탭에서 영수증 분석 필요" if pending_receipts else None,
    ))

    # 7. Activity fee records — exclude cancelled/excluded records (removed participants)
    period_key = f"act-{str(activity_id)[:8]}"
    fee_records = list(db.scalars(
        select(PaymentRecord).where(
            and_(
                PaymentRecord.period == period_key,
                PaymentRecord.payment_type == "activity_fee",
                PaymentRecord.status.notin_(INACTIVE_ACTIVITY_FEE_STATUSES),
                PaymentRecord.member_id.in_([p.member_id for p in participants if p.member_id]),
            )
        )
    ))
    paid_count = sum(1 for r in fee_records if r.status == "paid")
    items.append(AuditCheckItem(
        key="activity_fee",
        label="활동비 납부 현황",
        done=len(fee_records) > 0,
        count=len(fee_records),
        detail=f"{paid_count}/{len(fee_records)} 납부" if fee_records else None,
    ))

    total_done = sum(1 for item in items if item.done)
    total_items = len(items)

    return ActivityAuditCheckResult(
        activity_id=str(activity_id),
        activity_title=report.title or "",
        items=items,
        total_done=total_done,
        total_items=total_items,
        ready_for_audit=total_done == total_items,
    )
