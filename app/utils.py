"""Utility functions."""

import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List


def get_directory_size(path: Path) -> int:
    """Return total size of all files in directory."""
    total = 0
    try:
        for item in path.rglob("*"):
            if item.is_file():
                total += item.stat().st_size
    except (PermissionError, OSError):
        pass
    return total


def is_vllm_installed() -> bool:
    """Check if vLLM package is available."""
    try:
        import importlib

        importlib.import_module("vllm")
        return True
    except ImportError:
        return False


def search_huggingface_models(query: str, limit: int = 50) -> Dict:
    """Search for text-generation models on HuggingFace."""
    try:
        from huggingface_hub import HfApi

        api = HfApi()
        models = list(
            api.list_models(search=query, limit=limit, sort="downloads", direction=-1)
        )

        results = []
        for m in models:
            tags = m.tags or []
            pipeline_tag = getattr(m, "pipeline_tag", "")
            is_text_model = any(
                kw in tags for kw in ["text-generation", "llm", "conversational"]
            ) or pipeline_tag in ["text-generation", "text2text-generation"]

            if is_text_model:
                results.append(
                    {
                        "id": m.id,
                        "name": m.id.split("/")[-1],
                        "author": m.author or "Unknown",
                        "downloads": m.downloads or 0,
                        "likes": m.likes or 0,
                        "tags": tags[:5],
                        "pipeline_tag": pipeline_tag or "text-generation",
                    }
                )

        return {"query": query, "results": results[:30], "count": len(results)}

    except ImportError:
        return {
            "query": query,
            "results": [],
            "count": 0,
            "warning": "Install huggingface_hub for model search",
        }


def get_local_models() -> Dict:
    """Scan local caches for downloaded models."""
    search_paths = [
        Path.home() / ".cache" / "huggingface" / "hub",
        Path.home() / ".cache" / "modelscope" / "hub",
        Path.home() / ".cache" / "mlx" / "models",
        Path.home() / "models",
    ]

    found: Dict[str, dict] = {}

    for search_path in search_paths:
        if search_path.exists():
            for item in search_path.iterdir():
                if not item.is_dir():
                    continue
                if item.name.startswith("models--"):
                    name = item.name.replace("models--", "").replace("--", "/")
                    found[name] = {
                        "name": name,
                        "path": str(item),
                        "size": get_directory_size(item),
                        "source": "huggingface",
                    }
                elif "/" in item.name or len(item.name.split(".")) >= 2:
                    found[item.name] = {
                        "name": item.name,
                        "path": str(item),
                        "size": get_directory_size(item),
                        "source": "local",
                    }

    try:
        from huggingface_hub import scan_cache_dir

        for repo in scan_cache_dir().repos:
            if repo.repo_id not in found:
                found[repo.repo_id] = {
                    "name": repo.repo_id,
                    "path": str(repo.repo_path),
                    "size": repo.size_on_disk or 0,
                    "source": "huggingface",
                }
    except ImportError:
        pass

    return {
        "models": list(found.values()),
        "total_count": len(found),
        "total_size": sum(m["size"] for m in found.values()),
    }


def delete_model_from_cache(model_name: str) -> bool:
    """Remove model from HuggingFace cache. Returns True on success."""
    try:
        from huggingface_hub import delete_repo

        try:
            delete_repo(repo_id=model_name)
            return True
        except Exception:
            pass

        cache = Path.home() / ".cache" / "huggingface" / "hub"
        dir_name = "models--" + model_name.replace("/", "--")
        model_path = cache / dir_name
        if model_path.exists():
            shutil.rmtree(model_path)
            return True
    except Exception:
        pass
    return False
