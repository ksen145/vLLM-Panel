"""vLLM Panel entry point."""

import sys
import io

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import uvicorn

from app.config import PANEL_PORT, VLLM_PORT
from app.utils import is_vllm_installed


def main() -> None:
    print("=" * 60)
    print("  vLLM Panel v4.0")
    print("  vLLM Manager (separate OpenAI-compatible service)")
    print("=" * 60)
    print()
    print(f"  Panel URL: http://localhost:{PANEL_PORT}")
    print(f"  vLLM API:  http://localhost:{VLLM_PORT}/v1")
    print()

    if is_vllm_installed():
        print("  vLLM: installed")
    else:
        print("  vLLM: NOT installed")
        print("    pip install vllm (Linux/Windows)")
        print("    pip install vllm-mlx (macOS)")

    print()
    print("=" * 60)

    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=PANEL_PORT,
        log_level="info",
        reload=False,
    )


if __name__ == "__main__":
    main()
