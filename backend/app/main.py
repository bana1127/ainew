from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import (
    activities,
    activity_categories,
    activity_reports,
    agents,
    assistant,
    automations,
    dashboard,
    files,
    health,
    members,
    notifications,
    payment_matching,
    payment_records,
    receipt_agents,
    receipts,
    reference_reports,
    settings as settings_router,
    transactions,
)


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
    app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])
    app.include_router(activities.router, prefix="/api/activities", tags=["activities"])
    app.include_router(members.router, prefix="/api/members", tags=["members"])
    app.include_router(
        activity_categories.router,
        prefix="/api/activity-categories",
        tags=["activity-categories"],
    )
    app.include_router(
        reference_reports.router,
        prefix="/api/reference-reports",
        tags=["reference-reports"],
    )
    app.include_router(
        activity_reports.router,
        prefix="/api/activity-reports",
        tags=["activity-reports"],
    )
    app.include_router(receipts.router, prefix="/api/receipts", tags=["receipts"])
    app.include_router(
        transactions.router,
        prefix="/api/transactions",
        tags=["transactions"],
    )
    app.include_router(
        payment_records.router,
        prefix="/api/payment-records",
        tags=["payment-records"],
    )
    app.include_router(
        payment_matching.router,
        prefix="/api/payments",
        tags=["payments"],
    )
    app.include_router(
        notifications.router,
        prefix="/api/notifications",
        tags=["notifications"],
    )
    app.include_router(settings_router.router, prefix="/api/settings", tags=["settings"])
    app.include_router(files.router, prefix="/api/files", tags=["files"])
    app.include_router(agents.router, prefix="/api/agents", tags=["agents"])
    app.include_router(receipt_agents.router, prefix="/api/agents", tags=["agents"])
    app.include_router(assistant.router, prefix="/api/assistant", tags=["assistant"])
    app.include_router(automations.router, prefix="/api/automations", tags=["automations"])

    @app.on_event("startup")
    def ensure_upload_directory() -> None:
        settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    @app.get("/")
    def root() -> dict[str, str]:
        return {"app": settings.APP_NAME, "status": "ok"}

    return app


app = create_app()
