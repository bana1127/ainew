"""Member merge service (Task 26).

Provides:
  find_duplicate_candidates(db) → list of duplicate groups
  merge_members(db, primary_id, duplicate_id) → move records, deactivate duplicate
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


@dataclass
class DuplicateGroup:
    reason: str  # same_student_id | same_phone | same_name_dept
    members: list[dict]  # [{id, name, student_id, phone, department, status, created_at}]


def find_duplicate_candidates(db: Session) -> list[DuplicateGroup]:
    """Return groups of members that are likely duplicates."""
    from app.models.member import Member

    groups: list[DuplicateGroup] = []
    seen_pairs: set[frozenset] = set()

    # 1. Same non-null student_id
    dup_sid = (
        select(Member.student_id)
        .where(Member.student_id.isnot(None), Member.status != "inactive")
        .group_by(Member.student_id)
        .having(func.count(Member.id) > 1)
    )
    for row in db.execute(dup_sid).all():
        sid = row[0]
        members = list(db.scalars(
            select(Member)
            .where(Member.student_id == sid, Member.status != "inactive")
            .order_by(Member.created_at.asc().nullsfirst())
        ))
        if len(members) < 2:
            continue
        pair = frozenset(str(m.id) for m in members)
        if pair in seen_pairs:
            continue
        seen_pairs.add(pair)
        groups.append(DuplicateGroup(
            reason="same_student_id",
            members=[_member_dict(m) for m in members],
        ))

    # 2. Same non-null phone
    dup_phone = (
        select(Member.phone)
        .where(Member.phone.isnot(None), Member.status != "inactive")
        .group_by(Member.phone)
        .having(func.count(Member.id) > 1)
    )
    for row in db.execute(dup_phone).all():
        phone = row[0]
        members = list(db.scalars(
            select(Member)
            .where(Member.phone == phone, Member.status != "inactive")
            .order_by(Member.created_at.asc().nullsfirst())
        ))
        if len(members) < 2:
            continue
        pair = frozenset(str(m.id) for m in members)
        if pair in seen_pairs:
            continue
        seen_pairs.add(pair)
        groups.append(DuplicateGroup(
            reason="same_phone",
            members=[_member_dict(m) for m in members],
        ))

    # 3. Same name + department
    dup_name_dept = (
        select(Member.name, Member.department)
        .where(
            Member.department.isnot(None),
            Member.status != "inactive",
        )
        .group_by(Member.name, Member.department)
        .having(func.count(Member.id) > 1)
    )
    for row in db.execute(dup_name_dept).all():
        name, dept = row[0], row[1]
        members = list(db.scalars(
            select(Member)
            .where(
                Member.name == name,
                Member.department == dept,
                Member.status != "inactive",
            )
            .order_by(Member.created_at.asc().nullsfirst())
        ))
        if len(members) < 2:
            continue
        pair = frozenset(str(m.id) for m in members)
        if pair in seen_pairs:
            continue
        seen_pairs.add(pair)
        groups.append(DuplicateGroup(
            reason="same_name_department",
            members=[_member_dict(m) for m in members],
        ))

    return groups


def merge_members(db: Session, primary_id: UUID, duplicate_id: UUID) -> dict:
    """Merge duplicate_id into primary_id.

    - Move ActivityParticipant, PaymentRecord to primary.
    - Null out student_id/phone on duplicate to avoid unique constraint.
    - Set duplicate.status = inactive.
    """
    from app.models.activity import ActivityParticipant
    from app.models.member import Member
    from app.models.payment import PaymentRecord

    primary = db.get(Member, primary_id)
    duplicate = db.get(Member, duplicate_id)

    if not primary:
        raise ValueError(f"Primary member not found: {primary_id}")
    if not duplicate:
        raise ValueError(f"Duplicate member not found: {duplicate_id}")
    if primary_id == duplicate_id:
        raise ValueError("primary_id and duplicate_id must be different")
    if duplicate.status == "inactive":
        raise ValueError("Duplicate member is already inactive")

    moved_participants = 0
    moved_payment_records = 0

    # Move ActivityParticipants
    dup_participants = list(db.scalars(
        select(ActivityParticipant).where(ActivityParticipant.member_id == duplicate_id)
    ))
    for p in dup_participants:
        conflict = db.scalar(
            select(ActivityParticipant).where(
                and_(
                    ActivityParticipant.activity_report_id == p.activity_report_id,
                    ActivityParticipant.member_id == primary_id,
                )
            )
        )
        if conflict:
            db.delete(p)
        else:
            p.member_id = primary_id
        moved_participants += 1

    # Move PaymentRecords
    dup_records = list(db.scalars(
        select(PaymentRecord).where(PaymentRecord.member_id == duplicate_id)
    ))
    for r in dup_records:
        conflict = db.scalar(
            select(PaymentRecord).where(
                and_(
                    PaymentRecord.member_id == primary_id,
                    PaymentRecord.period == r.period,
                    PaymentRecord.payment_type == r.payment_type,
                )
            )
        )
        if conflict:
            db.delete(r)
        else:
            r.member_id = primary_id
        moved_payment_records += 1

    # Fill missing fields on primary from duplicate
    if not primary.phone and duplicate.phone:
        primary.phone = duplicate.phone
    if not primary.email and duplicate.email:
        primary.email = duplicate.email
    if not primary.department and duplicate.department:
        primary.department = duplicate.department
    if not primary.student_id and duplicate.student_id:
        primary.student_id = duplicate.student_id

    # Null out unique fields on duplicate to avoid constraint violations
    duplicate.student_id = None
    duplicate.phone = None

    # Soft-delete duplicate
    duplicate.status = "inactive"

    db.flush()
    return {
        "primary_id": str(primary_id),
        "duplicate_id": str(duplicate_id),
        "moved_participants": moved_participants,
        "moved_payment_records": moved_payment_records,
    }


def _member_dict(m) -> dict:
    return {
        "id": str(m.id),
        "name": m.name,
        "student_id": m.student_id,
        "phone": m.phone,
        "department": m.department,
        "status": m.status,
        "created_at": str(m.created_at) if m.created_at else None,
    }
