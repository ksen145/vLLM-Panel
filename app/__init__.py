"""vLLM Panel - Multiplatform web management interface for vLLM."""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app import routes
from app.config import PANEL_PORT, STATIC_DIR

__version__ = "4.0.0"


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    application = FastAPI(title="vLLM Panel", version=__version__)
    application.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    application.include_router(routes.router)
    return application


app = create_app()
