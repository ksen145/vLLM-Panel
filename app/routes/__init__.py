"""Combine all route sub-modules into a single APIRouter."""

from fastapi import APIRouter

from app.routes.chat import router as chat_router
from app.routes.metrics import router as metrics_router
from app.routes.models import router as models_router
from app.routes.page import router as page_router
from app.routes.server import router as server_router

router = APIRouter()
router.include_router(page_router)
router.include_router(server_router)
router.include_router(models_router)
router.include_router(chat_router)
router.include_router(metrics_router)
