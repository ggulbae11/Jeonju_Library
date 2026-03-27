from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes.auth import router as auth_router
from backend.api.routes.books import router as books_router
from backend.api.routes.health import router as health_router
from backend.api.routes.imports import router as imports_router
from backend.api.routes.libraries import router as libraries_router
from backend.core.config import get_settings
from backend.services.import_service import bootstrap_database

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    bootstrap_database()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        description="Backend for the Jeonju library availability app",
        version="0.2.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router)
    app.include_router(auth_router, prefix=settings.api_prefix)
    app.include_router(libraries_router, prefix=settings.api_prefix)
    app.include_router(books_router, prefix=settings.api_prefix)
    app.include_router(imports_router, prefix=settings.api_prefix)
    return app


app = create_app()
