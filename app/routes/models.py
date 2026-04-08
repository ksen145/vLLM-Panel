"""Model management endpoints (local, search, download, delete)."""

import time
from typing import Any, Dict

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.models import ModelDownloadRequest
from app.server_manager import server_manager
from app.utils import (
    delete_model_from_cache,
    get_local_models,
    search_huggingface_models,
)

router = APIRouter()


@router.get("/api/models/local")
async def local_models() -> Dict[str, Any]:
    return get_local_models()


@router.get("/api/models/search")
async def search_models(query: str) -> Dict[str, Any]:
    return search_huggingface_models(query)


@router.post("/api/models/download")
async def download_model(
    req: ModelDownloadRequest, bg: BackgroundTasks
) -> Dict[str, Any]:
    model_name = req.model_name
    if model_name in server_manager.download_progress:
        prog = server_manager.download_progress[model_name]
        if prog.get("status") in ("downloading", "queued"):
            return {"status": "already_downloading"}
    bg.add_task(_download_model_task, model_name)
    return {"status": "started", "model": model_name}


def _download_model_task(model_name: str) -> None:
    try:
        from huggingface_hub import snapshot_download

        server_manager.download_progress[model_name] = {
            "status": "downloading",
            "model": model_name,
            "progress": 0,
            "started_at": time.time(),
        }
        start = time.time()

        def _hook(_fn: str, total: int, dl: int) -> None:
            progress = (
                (dl / total * 100)
                if total > 0
                else min(95, (time.time() - start) / 60 * 10)
            )
            server_manager.download_progress[model_name].update(
                {
                    "progress": progress,
                    "downloaded": dl,
                    "total": total,
                    "speed": dl / (time.time() - start) if time.time() > start else 0,
                    "elapsed": time.time() - start,
                }
            )

        snapshot_download(repo_id=model_name, local_dir_use_symlinks=False)
        server_manager.download_progress[model_name] = {
            "status": "completed",
            "model": model_name,
            "progress": 100,
            "completed_at": time.time(),
        }
        print(f"[OK] Downloaded {model_name}")

    except Exception as exc:
        server_manager.download_progress[model_name] = {
            "status": "failed",
            "model": model_name,
            "progress": 0,
            "error": str(exc),
        }
        print(f"[ERROR] Download failed {model_name}: {exc}")


@router.get("/api/models/download-progress/{model_name:path}")
async def download_progress(model_name: str) -> Dict[str, Any]:
    return server_manager.download_progress.get(model_name, {"status": "not_found"})


@router.delete("/api/models/{model_name:path}")
async def delete_model(model_name: str) -> Dict[str, Any]:
    if delete_model_from_cache(model_name):
        return {"status": "deleted"}
    raise HTTPException(status_code=404, detail="Model not found")
