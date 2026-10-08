"""FastAPI application for LeadForge."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Origins the LeadForge console (Next.js dev/prod) may call the API from.
CORS_ORIGINS = [
    "http://localhost:3000", "http://127.0.0.1:3000",
    "http://localhost:3001", "http://127.0.0.1:3001",
    "http://localhost:3005", "http://127.0.0.1:3005",
    "http://localhost:3006", "http://127.0.0.1:3006",
]

from app.config import settings
from app.logging_conf import setup_logging
from app.api.routers.campaigns import router as campaigns_router
from app.api.routers.leads import router as leads_router
from app.api.routers.messages import router as messages_router
from app.api.routers.suppression_routes import router as suppression_router
from app.api.routers.webhooks import router as webhooks_router
from app.api.routers.system import router as system_router
from app.api.routers.unsubscribe import router as unsubscribe_router
from app.api.routers.queue import router as queue_router
from app.api.routers.inbox import router as inbox_router
from app.api.routers.calls import router as calls_router
from app.api.routers.integrations import router as integrations_router
from app.api.routers.locations import router as locations_router
from app.api.routers.settings_routes import router as settings_router


def create_app() -> FastAPI:
    setup_logging()
    app = FastAPI(title=settings.app_name, version="0.2.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health():
        return {"status": "ok", "env": settings.app_env, "force_dry_run": settings.force_dry_run}

    app.include_router(campaigns_router)
    app.include_router(leads_router)
    app.include_router(messages_router)
    app.include_router(suppression_router)
    app.include_router(webhooks_router)
    app.include_router(system_router)
    app.include_router(unsubscribe_router)
    app.include_router(queue_router)
    app.include_router(inbox_router)
    app.include_router(calls_router)
    app.include_router(integrations_router)
    app.include_router(locations_router)
    app.include_router(settings_router)
    return app


app = create_app()
