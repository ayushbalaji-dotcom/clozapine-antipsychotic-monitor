from fastapi import FastAPI, Request
from .config import get_settings
from .logging_config import configure_logging
from .database import init_db, get_sessionmaker
from .auth import ensure_default_admin
from .api.health import router as health_router
from .api.auth import router as auth_router
from .api.scheduling import router as scheduling_router
from .api.webhooks import router as webhooks_router
from .api.worklist import router as worklist_router
from .api.tasks import router as tasks_router
from .api.admin import router as admin_router
from .api.audit import router as audit_router
from .api.uploads import router as uploads_router


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings)

    app = FastAPI(title="NHS Antipsychotic Monitoring Tracker", version="0.1.0")

    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        import uuid

        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    @app.on_event("startup")
    def startup() -> None:
        init_db()
        SessionLocal = get_sessionmaker()
        db = SessionLocal()
        try:
            ensure_default_admin(db)
        finally:
            db.close()

    app.include_router(health_router, prefix="/api/v1")
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(scheduling_router, prefix="/api/v1")
    app.include_router(webhooks_router, prefix="/api/v1")
    app.include_router(worklist_router, prefix="/api/v1")
    app.include_router(tasks_router, prefix="/api/v1")
    app.include_router(admin_router, prefix="/api/v1")
    app.include_router(audit_router, prefix="/api/v1")
    app.include_router(uploads_router, prefix="/api/v1")

    return app


app = create_app()
