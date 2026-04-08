"""Model management endpoints (local, search, download, delete)."""

import time
from typing import Any, Dict

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.models import ModelDownloadRequest, ModelFileRequest
from app.server_manager import server_manager
from app.utils import (
    delete_model_from_cache,
    get_local_models,
    search_huggingface_models,
    get_model_files,
    get_local_model_files,
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
    filename = req.filename or ""
    key = f"{model_name}:{filename}" if filename else model_name
    
    if key in server_manager.download_progress:
        prog = server_manager.download_progress[key]
        if prog.get("status") in ("downloading", "queued"):
            return {"status": "already_downloading"}
    bg.add_task(_download_model_task, model_name, filename, key)
    return {"status": "started", "model": model_name, "filename": filename, "key": key}


def _download_model_task(model_name: str, filename: str = "", key: str = "") -> None:
    if not key:
        key = f"{model_name}:{filename}" if filename else model_name

    class DownloadCancelled(Exception):
        pass

    try:
        from huggingface_hub import snapshot_download, hf_hub_download

        server_manager.download_progress[key] = {
            "status": "downloading",
            "model": model_name,
            "filename": filename,
            "progress": 0,
            "started_at": time.time(),
            "cancel_requested": False,
        }
        start = time.time()

        def _hook(_fn: str, total: int, dl: int) -> None:
            # Check for cancellation
            if server_manager.download_progress.get(key, {}).get("cancel_requested"):
                raise DownloadCancelled("Download was cancelled by user")

            progress = (
                (dl / total * 100)
                if total > 0
                else min(95, (time.time() - start) / 60 * 10)
            )
            server_manager.download_progress[key].update(
                {
                    "progress": progress,
                    "downloaded": dl,
                    "total": total,
                    "speed": dl / (time.time() - start) if time.time() > start else 0,
                    "elapsed": time.time() - start,
                }
            )

        if filename:
            # Download specific file
            hf_hub_download(
                repo_id=model_name,
                filename=filename,
                local_dir_use_symlinks=False,
            )
        else:
            # Download entire model
            snapshot_download(repo_id=model_name, local_dir_use_symlinks=False)

        # Check cancellation after download completes (edge case)
        if server_manager.download_progress.get(key, {}).get("cancel_requested"):
            raise DownloadCancelled("Download was cancelled by user")

        server_manager.download_progress[key] = {
            "status": "completed",
            "model": model_name,
            "filename": filename,
            "progress": 100,
            "completed_at": time.time(),
        }
        print(f"[OK] Downloaded {model_name}" + (f"/{filename}" if filename else ""))

    except DownloadCancelled:
        server_manager.download_progress[key] = {
            "status": "cancelled",
            "model": model_name,
            "filename": filename,
            "progress": server_manager.download_progress[key].get("progress", 0),
            "cancelled_at": time.time(),
        }
        # Clean up partial downloads
        _cleanup_partial_download(model_name, filename)
        print(f"[CANCEL] Download cancelled: {model_name}" + (f"/{filename}" if filename else ""))

    except Exception as exc:
        # Don't overwrite cancelled status
        current = server_manager.download_progress.get(key, {})
        if current.get("status") != "cancelled":
            server_manager.download_progress[key] = {
                "status": "failed",
                "model": model_name,
                "filename": filename,
                "progress": 0,
                "error": str(exc),
            }
        print(f"[ERROR] Download failed {model_name}: {exc}")


def _cleanup_partial_download(model_name: str, filename: str = "") -> None:
    """Remove partially downloaded files."""
    try:
        from pathlib import Path
        from huggingface_hub.constants import HF_HUB_CACHE

        cache_dir = Path(HF_HUB_CACHE)

        # Clean up snapshots and blobs for this model
        if cache_dir.exists():
            # Remove .locks
            locks_dir = cache_dir / ".locks"
            if locks_dir.exists():
                import shutil
                shutil.rmtree(locks_dir, ignore_errors=True)

            # Remove incomplete downloads (files in .tmp or with no commit)
            for item in cache_dir.iterdir():
                if item.name.startswith("models--") and model_name.replace("/", "--") in item.name:
                    # Only remove if download wasn't completed
                    refs_dir = item / "refs"
                    if not refs_dir.exists() or not any(refs_dir.iterdir()):
                        import shutil
                        shutil.rmtree(item, ignore_errors=True)
                        print(f"[CLEANUP] Removed partial download: {item.name}")
    except Exception as e:
        print(f"[WARN] Cleanup error: {e}")


@router.get("/api/models/local-files/{model_name:path}")
async def local_model_files(model_name: str) -> Dict[str, Any]:
    return get_local_model_files(model_name)


@router.delete("/api/models/download/{key:path}")
async def cancel_download(key: str) -> Dict[str, Any]:
    """Cancel an active download."""
    if server_manager.cancel_download(key):
        return {"status": "cancelled", "key": key}
    raise HTTPException(status_code=404, detail="Download not found")


@router.get("/api/models/files/{model_name:path}")
async def model_files(model_name: str) -> Dict[str, Any]:
    return get_model_files(model_name)


@router.get("/api/models/download-progress/{key:path}")
async def download_progress(key: str) -> Dict[str, Any]:
    # key can be "model_name" or "model_name:filename"
    # Try direct lookup first
    if key in server_manager.download_progress:
        return server_manager.download_progress[key]
    # Try to find by model name prefix
    for k, prog in server_manager.download_progress.items():
        if k == key or k.startswith(key + ":"):
            return prog
    return {"status": "not_found"}


@router.get("/api/models/downloads")
async def all_downloads() -> Dict[str, Any]:
    """Get all download progress (active and recent)."""
    result = []
    for name, prog in server_manager.download_progress.items():
        result.append({
            "key": name,
            "model": prog.get("model", ""),
            "filename": prog.get("filename", ""),
            "status": prog.get("status", ""),
            "progress": prog.get("progress", 0),
            "speed": prog.get("speed", 0),
            "elapsed": prog.get("elapsed", 0),
            "downloaded": prog.get("downloaded", 0),
            "total": prog.get("total", 0),
            "error": prog.get("error", ""),
        })
    return {"downloads": result}


@router.delete("/api/models/{model_name:path}")
async def delete_model(model_name: str) -> Dict[str, Any]:
    if delete_model_from_cache(model_name):
        return {"status": "deleted"}
    raise HTTPException(status_code=404, detail="Model not found")
