from fastapi import APIRouter

from app.core.config import settings
from app.core.database import check_database


router = APIRouter()


@router.get("/health")
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "database": check_database(),
    }

