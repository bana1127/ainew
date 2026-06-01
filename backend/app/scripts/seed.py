import json
from pathlib import Path
from typing import Any

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models import ActivityCategory, AppSetting, Member


DATA_DIR = Path(__file__).resolve().parents[1] / "data"


SAMPLE_MEMBERS = [
    {
        "name": "김가온",
        "student_id": "20260001",
        "department": "컴퓨터공학과",
        "status": "active",
    },
    {
        "name": "이도윤",
        "student_id": "20260002",
        "department": "소프트웨어학부",
        "status": "active",
    },
    {
        "name": "박서연",
        "student_id": "20260003",
        "department": "경영학과",
        "status": "active",
    },
    {
        "name": "최하준",
        "student_id": "20260004",
        "department": "디자인학과",
        "status": "active",
    },
    {
        "name": "정다온",
        "student_id": "20260005",
        "department": "전자공학과",
        "status": "active",
    },
]


def load_json(filename: str) -> list[dict[str, Any]]:
    path = DATA_DIR / filename
    return json.loads(path.read_text(encoding="utf-8"))


def seed_activity_categories() -> int:
    inserted = 0
    categories = load_json("seed_categories.json")

    with SessionLocal() as db:
        for item in categories:
            exists = db.scalar(
                select(ActivityCategory).where(ActivityCategory.name == item["name"])
            )
            if exists:
                continue

            db.add(ActivityCategory(**item))
            inserted += 1

        db.commit()

    return inserted


def seed_app_settings() -> int:
    inserted = 0
    settings = load_json("seed_settings.json")

    with SessionLocal() as db:
        for item in settings:
            exists = db.scalar(select(AppSetting).where(AppSetting.key == item["key"]))
            if exists:
                continue

            db.add(AppSetting(**item))
            inserted += 1

        db.commit()

    return inserted


def seed_members() -> int:
    inserted = 0

    with SessionLocal() as db:
        for item in SAMPLE_MEMBERS:
            exists = db.scalar(
                select(Member).where(Member.student_id == item["student_id"])
            )
            if exists:
                continue

            db.add(Member(**item))
            inserted += 1

        db.commit()

    return inserted


def main() -> None:
    results = {
        "activity_categories": seed_activity_categories(),
        "app_settings": seed_app_settings(),
        "members": seed_members(),
    }

    print("Seed completed")
    for key, count in results.items():
        print(f"- {key}: inserted {count}")


if __name__ == "__main__":
    main()

