from collections.abc import Generator

from sqlalchemy import create_engine, func, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


engine: Engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_database() -> str:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return "available"
    except SQLAlchemyError:
        return "unavailable"


def get_table_counts() -> dict[str, int]:
    from app.models import ActivityCategory, Member

    try:
        with SessionLocal() as db:
            return {
                "members": db.scalar(select(func.count(Member.id))) or 0,
                "activity_categories": db.scalar(
                    select(func.count(ActivityCategory.id))
                )
                or 0,
            }
    except SQLAlchemyError:
        return {}
