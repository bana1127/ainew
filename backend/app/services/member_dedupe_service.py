"""Member deduplication service.

Merges duplicate Member records that share the same student_id.
Safe to run multiple times (idempotent).

Usage:
    from app.services.member_dedupe_service import merge_duplicate_members
    result = merge_duplicate_members(db)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import and_, func, select, update
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


@dataclass
class MergeResult:
    scanned: int
    merged_groups: int
    merged_members: int
    moved_participants: int
    moved_payment_records: int


def merge_duplicate_members(db: Session, dry_run: bool = False) -> MergeResult:
    """Find members with the same non-null student_id and merge them.

    Strategy:
    - Oldest created_at member becomes the primary (canonical) record.
    - All activity_participants and payment_records pointing to duplicates
      are re-pointed to the primary.
    - Duplicate members are soft-deleted (status='inactive') rather than
      hard-deleted so historical data is preserved.
    """
    from app.models.activity import ActivityParticipant
    from app.models.member import Member
    from app.models.payment import PaymentRecord

    # Find student_ids that appear more than once
    dup_stmt = (
        select(Member.student_id, func.count(Member.id).label("cnt"))
        .where(Member.student_id.isnot(None))
        .group_by(Member.student_id)
        .having(func.count(Member.id) > 1)
    )
    dup_rows = list(db.execute(dup_stmt).all())

    total_merged_groups = 0
    total_merged_members = 0
    total_moved_participants = 0
    total_moved_payment_records = 0

    for dup_row in dup_rows:
        student_id = dup_row[0]
        members = list(db.scalars(
            select(Member)
            .where(Member.student_id == student_id)
            .order_by(Member.created_at.asc().nullsfirst())
        ))
        if len(members) < 2:
            continue

        primary = members[0]  # oldest = canonical
        duplicates = members[1:]

        logger.info(
            "Merging %d duplicates for student_id=%s → primary=%s",
            len(duplicates), student_id, primary.id,
        )

        for dup in duplicates:
            if not dry_run:
                # Re-point ActivityParticipants
                # Guard against duplicate (primary, activity) pairs
                dup_participants = list(db.scalars(
                    select(ActivityParticipant).where(
                        ActivityParticipant.member_id == dup.id
                    )
                ))
                for p in dup_participants:
                    conflict = db.scalar(
                        select(ActivityParticipant).where(
                            and_(
                                ActivityParticipant.activity_report_id == p.activity_report_id,
                                ActivityParticipant.member_id == primary.id,
                            )
                        )
                    )
                    if conflict:
                        db.delete(p)
                    else:
                        p.member_id = primary.id
                    total_moved_participants += 1

                # Re-point PaymentRecords
                # Guard against unique constraint (member_id, period, payment_type)
                dup_records = list(db.scalars(
                    select(PaymentRecord).where(PaymentRecord.member_id == dup.id)
                ))
                for r in dup_records:
                    conflict = db.scalar(
                        select(PaymentRecord).where(
                            and_(
                                PaymentRecord.member_id == primary.id,
                                PaymentRecord.period == r.period,
                                PaymentRecord.payment_type == r.payment_type,
                            )
                        )
                    )
                    if conflict:
                        db.delete(r)
                    else:
                        r.member_id = primary.id
                    total_moved_payment_records += 1

                # Fill missing fields on primary
                if not primary.phone and dup.phone:
                    primary.phone = dup.phone
                if not primary.email and dup.email:
                    primary.email = dup.email
                if not primary.department and dup.department:
                    primary.department = dup.department

                # Soft-delete the duplicate
                dup.status = "inactive"

                db.flush()

            total_merged_members += 1

        total_merged_groups += 1

    if not dry_run:
        db.commit()

    return MergeResult(
        scanned=len(dup_rows),
        merged_groups=total_merged_groups,
        merged_members=total_merged_members,
        moved_participants=total_moved_participants,
        moved_payment_records=total_moved_payment_records,
    )
