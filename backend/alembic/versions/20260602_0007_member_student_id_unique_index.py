"""task23: partial unique index on members.student_id, normalize existing values

Revision ID: 20260602_0007
Revises: 20260601_0006
Create Date: 2026-06-02 00:00:00

Hotfix (2026-06-02): duplicate member's student_id must be set to NULL before
the partial unique index is created, otherwise inactive rows still violate the
constraint (index condition is `student_id IS NOT NULL`, not `status = active`).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

revision: str = "20260602_0007"
down_revision: Union[str, None] = "20260601_0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # ── Step 1. Normalize student_id to pure digits ────────────────────────
    conn.execute(text(r"""
        UPDATE members
        SET student_id = regexp_replace(
                regexp_replace(trim(student_id), '\.0$', ''),
                '[^0-9]', '', 'g'
            )
        WHERE student_id IS NOT NULL
          AND student_id != ''
          AND student_id ~ '[0-9]'
    """))

    # Clear any student_id that became empty after normalization
    conn.execute(text("""
        UPDATE members
        SET student_id = NULL
        WHERE student_id = ''
    """))

    # ── Step 2. Move activity_participants from duplicates → primary ───────
    # For each (activity_report_id, dup_member) where primary_member participant
    # does NOT yet exist → reassign member_id to primary.
    conn.execute(text("""
        WITH ranked AS (
            SELECT id, student_id,
                   ROW_NUMBER() OVER (
                       PARTITION BY student_id
                       ORDER BY created_at ASC NULLS LAST, id ASC
                   ) AS rn
            FROM members
            WHERE student_id IS NOT NULL
        ),
        primaries AS (SELECT student_id, id AS primary_id FROM ranked WHERE rn = 1),
        dups      AS (
            SELECT r.id AS dup_id, p.primary_id
            FROM ranked r JOIN primaries p ON p.student_id = r.student_id
            WHERE r.rn > 1
        )
        UPDATE activity_participants ap
        SET member_id = d.primary_id
        FROM dups d
        WHERE ap.member_id = d.dup_id
          AND NOT EXISTS (
              SELECT 1 FROM activity_participants ap2
              WHERE ap2.activity_report_id = ap.activity_report_id
                AND ap2.member_id = d.primary_id
          )
    """))

    # Delete duplicate participants that couldn't be moved (conflict existed)
    conn.execute(text("""
        WITH ranked AS (
            SELECT id, student_id,
                   ROW_NUMBER() OVER (
                       PARTITION BY student_id
                       ORDER BY created_at ASC NULLS LAST, id ASC
                   ) AS rn
            FROM members
            WHERE student_id IS NOT NULL
        ),
        dup_ids AS (SELECT id FROM ranked WHERE rn > 1)
        DELETE FROM activity_participants
        WHERE member_id IN (SELECT id FROM dup_ids)
    """))

    # ── Step 3. Move payment_records from duplicates → primary ────────────
    conn.execute(text("""
        WITH ranked AS (
            SELECT id, student_id,
                   ROW_NUMBER() OVER (
                       PARTITION BY student_id
                       ORDER BY created_at ASC NULLS LAST, id ASC
                   ) AS rn
            FROM members
            WHERE student_id IS NOT NULL
        ),
        primaries AS (SELECT student_id, id AS primary_id FROM ranked WHERE rn = 1),
        dups      AS (
            SELECT r.id AS dup_id, p.primary_id
            FROM ranked r JOIN primaries p ON p.student_id = r.student_id
            WHERE r.rn > 1
        )
        UPDATE payment_records pr
        SET member_id = d.primary_id
        FROM dups d
        WHERE pr.member_id = d.dup_id
          AND NOT EXISTS (
              SELECT 1 FROM payment_records pr2
              WHERE pr2.member_id = d.primary_id
                AND pr2.period = pr.period
                AND pr2.payment_type = pr.payment_type
          )
    """))

    # Delete conflicting payment_records that could not be moved
    conn.execute(text("""
        WITH ranked AS (
            SELECT id, student_id,
                   ROW_NUMBER() OVER (
                       PARTITION BY student_id
                       ORDER BY created_at ASC NULLS LAST, id ASC
                   ) AS rn
            FROM members
            WHERE student_id IS NOT NULL
        ),
        dup_ids AS (SELECT id FROM ranked WHERE rn > 1)
        DELETE FROM payment_records
        WHERE member_id IN (SELECT id FROM dup_ids)
    """))

    # ── Step 4. Soft-delete duplicate members AND null their student_id ────
    # CRITICAL: student_id must be set to NULL so the partial unique index
    # (WHERE student_id IS NOT NULL) is not violated by inactive rows.
    conn.execute(text("""
        WITH ranked AS (
            SELECT id, student_id,
                   ROW_NUMBER() OVER (
                       PARTITION BY student_id
                       ORDER BY created_at ASC NULLS LAST, id ASC
                   ) AS rn
            FROM members
            WHERE student_id IS NOT NULL
        ),
        dup_ids AS (SELECT id, student_id FROM ranked WHERE rn > 1)
        UPDATE members m
        SET
            status     = 'inactive',
            student_id = NULL,
            memo       = concat(
                             coalesce(m.memo, ''),
                             ' / merged duplicate student_id: ',
                             d.student_id
                         )
        FROM dup_ids d
        WHERE m.id = d.id
    """))

    # ── Step 5. Pre-flight validation ─────────────────────────────────────
    # Assert that no student_id duplicates remain before creating the index.
    result = conn.execute(text("""
        SELECT student_id, COUNT(*) AS cnt
        FROM members
        WHERE student_id IS NOT NULL
        GROUP BY student_id
        HAVING COUNT(*) > 1
    """)).fetchall()

    if result:
        dups_desc = ", ".join(f"{row[0]}({row[1]})" for row in result[:5])
        raise RuntimeError(
            f"Cannot create unique index: {len(result)} student_id(s) still "
            f"have duplicates after cleanup: {dups_desc}. "
            "Run member_dedupe_service.merge_duplicate_members(db) and retry."
        )

    # ── Step 6. Create partial unique index ───────────────────────────────
    op.create_index(
        "uq_members_student_id_not_null",
        "members",
        ["student_id"],
        unique=True,
        postgresql_where=sa.text("student_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_members_student_id_not_null", table_name="members")
