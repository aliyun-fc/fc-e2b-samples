"""Browser Studio API application."""

from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.browser.routes import router as runs_router
from src.browser.service import BrowserService
from src.core.runs import RunStore
from src.core.settings import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.runs = RunStore()
    app.state.browser_service = BrowserService(get_settings(), app.state.runs)
    yield
    await app.state.runs.close_all()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="E2B Browser Studio", version="0.1.0", lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["*"], allow_headers=["*"])
    app.include_router(runs_router)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app


app = create_app()


def run() -> None:
    settings = get_settings()
    uvicorn.run("src.main:app", host=settings.studio_host, port=settings.studio_port, reload=True)
