"""Page and panel info endpoints."""

import sys
import time
from typing import Any, Dict

from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.config import PANEL_PORT, STATIC_DIR, VLLM_PORT
from app.server_manager import server_manager
from app.utils import is_vllm_installed

router = APIRouter()


@router.get("/")
async def index():
    return FileResponse(str(STATIC_DIR / "index.html"))


def _platform_display_name() -> str:
    if sys.platform == "darwin":
        return "macOS Apple Silicon"
    if sys.platform == "win32":
        return "Windows"
    return "Linux"


@router.get("/api/info")
async def get_info() -> Dict[str, Any]:
    return {
        "version": "4.0.0",
        "platform": sys.platform,
        "platform_name": _platform_display_name(),
        "python_version": sys.version,
        "vllm_available": is_vllm_installed(),
        "panel_port": PANEL_PORT,
        "vllm_port": VLLM_PORT,
        "server": {
            "is_running": server_manager.is_running,
            "model": server_manager.model,
            "pid": server_manager.pid,
            "start_time": server_manager.start_time,
            "uptime": (
                time.time() - server_manager.start_time
                if server_manager.start_time
                else 0
            ),
        },
    }
