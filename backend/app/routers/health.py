from fastapi import APIRouter

from app.core.config import settings
from app.core.database import check_database, get_table_counts


router = APIRouter()


@router.get("/health")
def health_check() -> dict[str, object]:
    database_status = check_database()

    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "database": database_status,
        "tables": get_table_counts() if database_status == "available" else {},
    }
