"""System and GPU metrics endpoint."""

import subprocess
import sys
from typing import Any, Dict

import psutil
from fastapi import APIRouter

from app.config import BASE_DIR
from app.server_manager import server_manager

router = APIRouter()


def _collect_gpu_metrics() -> Dict[str, Any]:
    if sys.platform == "darwin":
        try:
            import mlx.core as mx  # noqa: F401

            return {"available": True, "backend": "Metal (Apple Silicon)"}
        except ImportError:
            return {"available": False}

    try:
        import torch

        if torch.cuda.is_available():
            gpus = []
            for i in range(torch.cuda.device_count()):
                props = torch.cuda.get_device_properties(i)
                allocated = torch.cuda.memory_allocated(i)
                reserved = torch.cuda.memory_reserved(i)
                gpus.append(
                    {
                        "index": i,
                        "name": props.name,
                        "memory_total": props.total_memory,
                        "memory_allocated": allocated,
                        "memory_reserved": reserved,
                        "memory_free": props.total_memory - reserved,
                        "memory_usage_percent": (
                            (reserved / props.total_memory * 100)
                            if props.total_memory > 0
                            else 0
                        ),
                    }
                )
            return {
                "available": True,
                "device_count": torch.cuda.device_count(),
                "gpus": gpus,
            }
        return {"available": False}

    except ImportError:
        try:
            r = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=utilization.gpu,memory.total,memory.used,memory.free,name",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if r.returncode == 0:
                gpus = []
                for i, line in enumerate(r.stdout.strip().split("\n")):
                    parts = [p.strip() for p in line.split(",")]
                    if len(parts) >= 5:
                        gpus.append(
                            {
                                "index": i,
                                "utilization": float(parts[0]),
                                "memory_total": float(parts[1]) * 1024 * 1024,
                                "memory_used": float(parts[2]) * 1024 * 1024,
                                "memory_free": float(parts[3]) * 1024 * 1024,
                                "name": parts[4],
                            }
                        )
                return {"available": True, "gpus": gpus}
            return {"available": False}
        except Exception:
            return {"available": False}


@router.get("/api/metrics")
async def get_metrics() -> Dict[str, Any]:
    proc = psutil.Process()

    return {
        "system": {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "cpu_count": psutil.cpu_count(),
            "cpu_freq": (psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None),
            "memory": psutil.virtual_memory()._asdict(),
            "disk": psutil.disk_usage(str(BASE_DIR))._asdict(),
        },
        "gpu": _collect_gpu_metrics(),
        "vllm_process": server_manager.get_process_metrics(),
        "panel_process": {
            "pid": proc.pid,
            "cpu_percent": proc.cpu_percent(interval=0.1),
            "memory_rss": proc.memory_info().rss,
        },
    }
