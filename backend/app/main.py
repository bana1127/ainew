from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import health


def create_app() -> FastAPI:
    app = FastAPI(title=settings.APP_NAME)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router, prefix="/api", tags=["health"])

    @app.on_event("startup")
    def ensure_upload_directory() -> None:
        settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    @app.get("/")
    def root() -> dict[str, str]:
        return {"app": settings.APP_NAME, "status": "ok"}

    return app


app = create_app()
