from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.health import router as health_router
from app.api.routes.parse import router as parse_router
from app.api.routes.scripts import router as scripts_router
from app.core.config import settings


def create_app() -> FastAPI:
    app = FastAPI(
        title="ScriptSense Backend",
        version="0.1.0",
        description="Rules-based screenplay parsing backend for ScriptSense.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    app.include_router(parse_router, prefix="/api/v1")
    app.include_router(scripts_router, prefix="/api/v1")
    return app


app = create_app()
