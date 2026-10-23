"""Application factory."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
from starlette.templating import Jinja2Templates

from app.config import Settings
from app.database import Base, make_engine, make_session_factory
from app.routers import api, web
from app.services import ensure_admin

TEMPLATES = Path(__file__).parent / "templates"


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the FastAPI app. Tests pass their own ``Settings`` (own DB file)."""
    settings = settings or Settings()
    engine = make_engine(settings.database_url)
    session_factory = make_session_factory(engine)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        Base.metadata.create_all(engine)
        with session_factory() as db:
            ensure_admin(db, settings.admin_username, settings.admin_password)
        yield
        engine.dispose()

    app = FastAPI(title="Order Desk", version="1.0.0", lifespan=lifespan)
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.secret_key,
        session_cookie="orderdesk_session",
        same_site="lax",
        https_only=settings.https_only_cookies,
    )
    app.state.session_factory = session_factory
    app.state.templates = Jinja2Templates(directory=str(TEMPLATES))
    app.include_router(api.router)
    app.include_router(web.router)
    return app


def app_factory() -> FastAPI:
    """Entry point for ``uvicorn app.main:app_factory --factory``."""
    return create_app()
