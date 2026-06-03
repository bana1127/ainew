from datetime import datetime
from uuid import UUID

from app.schemas.common import ORMModel


class MemberBase(ORMModel):
    name: str
    student_id: str | None = None
    department: str | None = None
    phone: str | None = None
    email: str | None = None
    status: str = "active"
    memo: str | None = None
    # Task 26-booster: member roster fields
    gender: str | None = None
    grade: str | None = None
    birth_year: int | None = None
    joined_term: str | None = None
    term_code: str | None = None
    is_executive: bool = False
    role: str | None = None
    is_officer: bool = False
    officer_role: str | None = None


class MemberCreate(MemberBase):
    pass


class MemberUpdate(ORMModel):
    name: str | None = None
    student_id: str | None = None
    department: str | None = None
    phone: str | None = None
    email: str | None = None
    status: str | None = None
    memo: str | None = None
    gender: str | None = None
    grade: str | None = None
    birth_year: int | None = None
    joined_term: str | None = None
    term_code: str | None = None
    is_executive: bool | None = None
    role: str | None = None
    is_officer: bool | None = None
    officer_role: str | None = None


class MemberRead(MemberBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
