"""Utility functions."""

import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List


def format_bytes(bytes: int) -> str:
    """Format bytes to human readable string."""
    if bytes == 0:
        return "0 B"
    k = 1024
    sizes = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    val = float(bytes)
    while val >= k and i < len(sizes) - 1:
        val /= k
        i += 1
    return f"{val:.2f} {sizes[i]}"


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


def get_model_files(model_name: str) -> Dict:
    """Get list of files for a model from HuggingFace using REST API."""
    try:
        import urllib.request
        import json
        
        # Use HuggingFace API directly
        url = f"https://huggingface.co/api/models/{model_name}/tree/main?recursive=true"
        
        req = urllib.request.Request(url, headers={
            'User-Agent': 'vLLM-Panel/4.0',
            'Accept': 'application/json'
        })
        
        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                data = json.loads(response.read().decode('utf-8'))
        except Exception as e:
            # Fallback: try without recursive
            url = f"https://huggingface.co/api/models/{model_name}/tree/main"
            req = urllib.request.Request(url, headers={
                'User-Agent': 'vLLM-Panel/4.0',
                'Accept': 'application/json'
            })
            with urllib.request.urlopen(req, timeout=15) as response:
                data = json.loads(response.read().decode('utf-8'))
        
        # Filter for model files only
        model_extensions = {'.gguf', '.bin', '.pt', '.pth', '.safetensors', '.onnx', '.h5', '.ckpt', '.pb', '.model'}
        skip_prefixes = {'.git', 'original/', 'images/'}
        
        model_files = []
        for item in data:
            if item.get('type') != 'file':
                continue
            
            path = item.get('path', '')
            
            # Skip metadata
            if any(path.startswith(p) for p in skip_prefixes):
                continue
            
            # Only include model files
            if not any(path.endswith(ext) for ext in model_extensions):
                continue
            
            # Get size from lfs info
            lfs = item.get('lfs', {})
            size = lfs.get('size', 0) if isinstance(lfs, dict) else 0
            
            model_files.append({
                "filename": path,
                "size": size,
                "size_human": format_bytes(size),
            })
        
        # Sort by size descending
        model_files.sort(key=lambda x: x["size"], reverse=True)
        
        return {"model": model_name, "files": model_files, "count": len(model_files)}
    
    except Exception as e:
        return {"error": str(e)}


def get_local_model_files(model_name: str) -> Dict:
    """Get list of files for a locally cached model."""
    # Search in known cache paths
    search_paths = [
        Path.home() / ".cache" / "huggingface" / "hub",
        Path.home() / ".cache" / "modelscope" / "hub",
        Path.home() / ".cache" / "mlx" / "models",
        Path.home() / "models",
    ]

    model_path = None

    for search_path in search_paths:
        if search_path.exists():
            # Check for HuggingFace style (models--org--name)
            hf_name = "models--" + model_name.replace("/", "--")
            hf_path = search_path / hf_name
            if hf_path.exists():
                model_path = hf_path
                break
            # Check for direct name match
            direct_path = search_path / model_name
            if direct_path.exists():
                model_path = direct_path
                break

    if model_path is None:
        return {"error": "Model path not found", "model": model_name}

    # List files
    files = []
    try:
        for item in model_path.rglob("*"):
            if item.is_file():
                rel = item.relative_to(model_path)
                files.append({
                    "filename": item.name,
                    "relative_path": str(rel),
                    "size": item.stat().st_size,
                    "size_human": format_bytes(item.stat().st_size),
                })
    except (PermissionError, OSError) as e:
        return {"error": str(e), "model": model_name}

    # Sort by name
    files.sort(key=lambda x: x["relative_path"])

    return {"model": model_name, "path": str(model_path), "files": files, "count": len(files)}


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
