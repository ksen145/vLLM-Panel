"""Application configuration constants."""

from pathlib import Path

PANEL_PORT = 8500
VLLM_PORT = 8001
LOG_MAX_LINES = 500

BASE_DIR = Path(__file__).parent.parent
STATIC_DIR = BASE_DIR / "static"
