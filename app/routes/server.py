"""vLLM server lifecycle management endpoints."""

import asyncio
import time
from typing import Any, Dict

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.config import VLLM_PORT
from app.models import ServerStartRequest
from app.server_manager import server_manager

router = APIRouter()


@router.post("/api/server/start")
async def start_server(req: ServerStartRequest) -> Dict[str, Any]:
    if server_manager.is_running:
        return {"status": "already_running", "model": server_manager.model}
    return server_manager.start(
        model=req.model,
        max_model_len=req.max_model_len,
        gpu_memory_utilization=req.gpu_memory_utilization,
        tensor_parallel_size=req.tensor_parallel_size,
        dtype=req.dtype,
        quantization=req.quantization,
        trust_remote_code=req.trust_remote_code,
        max_num_batched_tokens=req.max_num_batched_tokens,
        enable_prefix_caching=req.enable_prefix_caching,
    )


@router.post("/api/server/stop")
async def stop_server() -> Dict[str, Any]:
    return server_manager.stop()


@router.get("/api/server/status")
async def server_status() -> Dict[str, Any]:
    uptime = time.time() - server_manager.start_time if server_manager.start_time else 0
    return {
        "is_running": server_manager.is_running,
        "model": server_manager.model,
        "pid": server_manager.pid,
        "port": VLLM_PORT,
        "start_time": server_manager.start_time,
        "uptime": uptime,
        "args": server_manager.args,
        "api_url": (
            f"http://localhost:{VLLM_PORT}/v1" if server_manager.is_running else None
        ),
    }


@router.get("/api/server/logs")
async def server_logs(lines: int = 100) -> Dict[str, Any]:
    return {"logs": server_manager.get_logs(lines)}


@router.get("/api/server/logs/stream")
async def stream_logs():
    async def log_generator():
        last_count = 0
        while True:
            with server_manager.log_lock:
                new_lines = server_manager.log_lines[last_count:]
                last_count = len(server_manager.log_lines)
            if new_lines:
                for line in new_lines:
                    yield f"data: {line}\n\n"
            await asyncio.sleep(0.5)

    return StreamingResponse(log_generator(), media_type="text/event-stream")
