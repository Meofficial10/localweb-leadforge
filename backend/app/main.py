"""FastAPI application for LeadForge."""
from __future__ import annotations

from fastapi import FastAPI

from app.config import settings
from app.logging_conf import setup_logging
from app.api.routers.campaigns import router as campaigns_router
from app.api.routers.leads import router as leads_router
from app.api.routers.messages import router as messages_router
from app.api.routers.suppression_routes import router as suppression_router
from app.api.routers.webhooks import router as webhooks_router
from app.api.routers.system import router as system_router
from app.api.routers.unsubscribe import router as unsubscribe_router


def create_app() -> FastAPI:
    setup_logging()
    app = FastAPI(title=settings.app_name, version="0.1.0")

    @app.get("/health")
    def health():
        return {"status": "ok", "env": settings.app_env}

    app.include_router(campaigns_router)
    app.include_router(leads_router)
    app.include_router(messages_router)
    app.include_router(suppression_router)
    app.include_router(webhooks_router)
    app.include_router(system_router)
    app.include_router(unsubscribe_router)
    return app


app = create_app()
