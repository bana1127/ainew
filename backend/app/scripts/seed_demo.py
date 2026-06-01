"""Demo seed script for ClubAgent.

Inserts sample members, activity categories, activity reports, and
reference reports for demonstration purposes.

Safe to run multiple times — duplicates are skipped by unique key.

Usage:
    python -m app.scripts.seed_demo
"""
from __future__ import annotations

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models import ActivityCategory, Member
from app.models.activity import ActivityReport, ReferenceReport


# ─── Demo data ────────────────────────────────────────────────────────────────

DEMO_MEMBERS = [
    {"name": "김가온",  "student_id": "20260101", "department": "컴퓨터공학과",   "status": "active"},
    {"name": "이도윤",  "student_id": "20260102", "department": "소프트웨어학부", "status": "active"},
    {"name": "박서연",  "student_id": "20260103", "department": "경영학과",       "status": "active"},
    {"name": "최하준",  "student_id": "20260104", "department": "디자인학과",     "status": "active"},
    {"name": "정민서",  "student_id": "20260105", "department": "전자공학과",     "status": "active"},
    {"name": "윤지호",  "student_id": "20260106", "department": "컴퓨터공학과",   "status": "active"},
    {"name": "한서아",  "student_id": "20260107", "department": "수학과",         "status": "active"},
    {"name": "강도현",  "student_id": "20260108", "department": "정보통신공학과", "status": "active"},
    {"name": "오하린",  "student_id": "20260109", "department": "물리학과",       "status": "active"},
    {"name": "문시우",  "student_id": "20260110", "department": "소프트웨어학부", "status": "active"},
]

DEMO_REPORTS = [
    {
        "title": "5월 AI 스터디",
        "activity_date": "2026-05-15",
        "location": "동아리방 B204",
        "status": "generated",
        "input_text": "Claude API 활용 실습, 팀원 토론, 개인 프로젝트 발표",
        "final_content": """5월 AI 스터디 활동 보고서

일시: 2026년 5월 15일 (수) 19:00 ~ 21:00
장소: 동아리방 B204
참석: 10명

## 활동 내용

1. Claude API 활용 실습
   - Anthropic Claude API 기본 사용법 소개
   - 팀원들이 직접 코드 작성 및 실습
   - 결과물 공유 및 피드백

2. 팀원 토론
   - AI 서비스 개발 방향 논의
   - 다음 프로젝트 아이디어 도출

3. 개인 프로젝트 발표
   - 3명 발표 (각 10분)
   - Q&A 및 개선 의견 공유

## 결과 및 다음 계획

- Claude API 실습 코드 GitHub 공유 완료
- 다음 스터디: 5월 29일 (RAG 구현 실습)
""",
    },
    {
        "title": "신입 부원 OT",
        "activity_date": "2026-03-10",
        "location": "강의실 304호",
        "status": "confirmed",
        "input_text": "신입 부원 오리엔테이션, 동아리 소개, 활동 계획 안내",
        "final_content": """2026년 신입 부원 오리엔테이션

일시: 2026년 3월 10일 (화) 18:00 ~ 20:00
장소: 강의실 304호
참석: 신입 8명, 기존 부원 5명

## 활동 내용

1. 동아리 소개 및 운영 방식 안내
2. 활동 계획 소개 (스터디, 프로젝트, 공모전)
3. 자기소개 및 관심 분야 공유
4. 팀 빌딩 활동

## 결과

- 신입 부원 공식 등록 완료
- 소그룹 구성 완료 (AI 스터디 / 웹 개발 / 앱 개발)
""",
    },
    {
        "title": "PBL-C 개발 회의",
        "activity_date": "2026-04-20",
        "location": "온라인 (Gather Town)",
        "status": "draft",
        "input_text": "ClubAgent 개발 회의, 백엔드 API 설계 논의, 역할 분담",
        "final_content": None,
    },
    {
        "title": "교내 공모전 준비 회의",
        "activity_date": "2026-05-28",
        "location": "도서관 스터디룸",
        "status": "generated",
        "input_text": "AI 아이디어 공모전 팀 구성, 주제 브레인스토밍, 발표 자료 분담",
        "final_content": """교내 AI 아이디어 공모전 준비 회의

일시: 2026년 5월 28일 (목) 14:00 ~ 16:00
장소: 도서관 스터디룸 3호

## 주요 내용

1. 공모전 주제 확정: "AI 기반 동아리 운영 자동화 시스템"
2. 팀 구성 (5명)
3. 역할 분담:
   - 발표 자료: 이도윤, 박서연
   - 시연 데모: 김가온, 최하준
   - 논문 요약: 정민서

## 다음 일정

- 1차 발표 자료 완성: 6월 5일
- 팀 내 리허설: 6월 10일
- 최종 제출: 6월 15일
""",
    },
]

DEMO_REFERENCES = [
    {
        "title": "정기 스터디 보고서 예시",
        "content": """정기 스터디 활동 보고서

일시: 20XX년 X월 X일 (요일) HH:00 ~ HH:00
장소: 동아리방
참석자: X명

## 활동 내용

1. 주제 발표 (X분)
2. 토론 및 Q&A (X분)
3. 다음 활동 계획 논의 (X분)

## 결과 요약

- 참석률: X%
- 학습 내용: ...
- 다음 주제: ...

## 개선 사항

- ...
""",
        "tags": ["스터디", "정기모임"],
    },
    {
        "title": "프로젝트 회의 보고서 예시",
        "content": """프로젝트 개발 회의 보고서

일시: 20XX년 X월 X일
참석: X명

## 논의 사항

1. 현재 진행 상황 공유
2. 이슈 및 해결 방안
3. 다음 마일스톤 설정

## 결정 사항

- ...

## 액션 아이템

| 담당자 | 작업 | 기한 |
|--------|------|------|
| ...    | ...  | ...  |
""",
        "tags": ["프로젝트", "개발회의"],
    },
    {
        "title": "신입 부원 OT 보고서 예시",
        "content": """신입 부원 오리엔테이션 보고서

일시: 20XX년 X월 X일
장소: 강의실 XXX호

## 프로그램

1. 동아리 소개 (XX분)
2. 활동 계획 안내
3. 자기소개
4. 팀 구성

## 참석 현황

- 신입: X명
- 기존: X명

## 결과

- ...
""",
        "tags": ["OT", "신입부원"],
    },
]


# ─── seed functions ───────────────────────────────────────────────────────────

def _get_or_create_category(db, name: str):
    """Return first category with name, or create a default one."""
    cat = db.execute(
        select(ActivityCategory).where(ActivityCategory.name == name)
    ).scalar_one_or_none()
    if cat is None:
        cat = db.execute(select(ActivityCategory).limit(1)).scalar_one_or_none()
    return cat


def seed_demo_members() -> int:
    inserted = 0
    with SessionLocal() as db:
        for m in DEMO_MEMBERS:
            exists = db.execute(
                select(Member).where(Member.student_id == m["student_id"])
            ).scalar_one_or_none()
            if exists is None:
                db.add(Member(**m))
                inserted += 1
        db.commit()
    return inserted


def seed_demo_reports() -> int:
    inserted = 0
    with SessionLocal() as db:
        for r in DEMO_REPORTS:
            exists = db.execute(
                select(ActivityReport).where(ActivityReport.title == r["title"])
            ).scalar_one_or_none()
            if exists is None:
                # Find any available category
                cat = db.execute(select(ActivityCategory).limit(1)).scalar_one_or_none()
                db.add(ActivityReport(
                    category_id=cat.id if cat else None,
                    title=r["title"],
                    activity_date=r["activity_date"],
                    location=r["location"],
                    status=r["status"],
                    input_text=r.get("input_text"),
                    final_content=r.get("final_content"),
                ))
                inserted += 1
        db.commit()
    return inserted


def seed_demo_references() -> int:
    inserted = 0
    with SessionLocal() as db:
        for ref in DEMO_REFERENCES:
            exists = db.execute(
                select(ReferenceReport).where(ReferenceReport.title == ref["title"])
            ).scalar_one_or_none()
            if exists is None:
                cat = db.execute(select(ActivityCategory).limit(1)).scalar_one_or_none()
                db.add(ReferenceReport(
                    category_id=cat.id if cat else None,
                    title=ref["title"],
                    content=ref["content"],
                    tags=ref.get("tags"),
                ))
                inserted += 1
        db.commit()
    return inserted


def main() -> None:
    print("=== ClubAgent Demo Seed ===")

    m = seed_demo_members()
    print(f"  Members:    {m} inserted")

    r = seed_demo_reports()
    print(f"  Reports:    {r} inserted")

    ref = seed_demo_references()
    print(f"  References: {ref} inserted")

    print("Done.")


if __name__ == "__main__":
    main()
