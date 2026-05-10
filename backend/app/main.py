"""FastAPI entry-point for the SJ Project Planner Agent."""
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from .config import settings
from .database import Base, engine, SessionLocal
from .routers import (attachments, auth, changes, clarifications, dashboard,
                      drafts, exports, notes, projects, tasks)
from .services.observability import (configure_logging, get_logger,
                                     instrument_app)
from .services.rate_limit import limiter
from .services.seed import seed_if_empty


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Attach a request id to every response and to structlog context."""
    async def dispatch(self, request: Request, call_next):
        import structlog
        rid = request.headers.get("x-request-id") or str(uuid.uuid4())
        structlog.contextvars.bind_contextvars(request_id=rid, path=request.url.path,
                                               method=request.method)
        try:
            response = await call_next(request)
        finally:
            structlog.contextvars.clear_contextvars()
        response.headers["x-request-id"] = rid
        return response


def create_app() -> FastAPI:
    configure_logging()
    log = get_logger(__name__)

    app = FastAPI(
        title="SJ Project Planner Agent",
        version="1.0.0",
        description=(
            "Agentic AI for task-progress and project tracking. Translates "
            "meeting notes / emails / chats into reviewed, auditable plan updates. "
            "Multi-tenant, JWT + Microsoft Entra ID compatible, instrumented for "
            "Azure Application Insights, with Microsoft Agent Framework patterns."
        ),
    )
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["x-request-id"],
    )

    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_if_empty(db)

    app.include_router(auth.router)
    app.include_router(projects.router)
    app.include_router(tasks.router)
    app.include_router(notes.router)
    app.include_router(attachments.router)
    app.include_router(drafts.router)
    app.include_router(changes.router)
    app.include_router(clarifications.router)
    app.include_router(dashboard.router)
    app.include_router(exports.router)

    @app.get("/api/health")
    def health():
        return {
            "status": "ok",
            "llm_enabled": settings.llm_enabled,
            "search_enabled": settings.search_enabled,
            "entra_enabled": settings.entra_enabled,
            "appinsights_enabled": settings.appinsights_enabled,
            "blob_storage_enabled": settings.blob_storage_enabled,
            "cosmos_enabled": settings.cosmos_enabled,
            "env": settings.app_env,
        }

    instrument_app(app)
    log.info("app_started", env=settings.app_env, llm=settings.llm_enabled,
             entra=settings.entra_enabled, appinsights=settings.appinsights_enabled)
    return app


app = create_app()
