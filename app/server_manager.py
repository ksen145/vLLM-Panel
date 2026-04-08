"""vLLM OpenAI server process manager."""

import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import psutil

from app.config import VLLM_PORT, LOG_MAX_LINES

IS_WINDOWS = sys.platform == "win32"


class VLLMServerManager:
    """Manages the vLLM OpenAI-compatible server subprocess."""

    def __init__(self) -> None:
        self.process: Optional[subprocess.Popen] = None
        self.pid: Optional[int] = None
        self.model: Optional[str] = None
        self.args: Dict[str, Any] = {}
        self.start_time: Optional[float] = None
        self.is_running: bool = False
        self.log_lines: List[str] = []
        self.log_lock = threading.Lock()
        self._log_thread: Optional[threading.Thread] = None

        self.download_progress: Dict[str, Dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # Process lifecycle
    # ------------------------------------------------------------------

    def start(self, model: str, **kwargs: Any) -> Dict[str, Any]:
        """Launch vLLM OpenAI server."""
        if self.is_running:
            return {
                "status": "already_running",
                "model": self.model,
                "port": VLLM_PORT,
            }

        cmd = [
            sys.executable,
            "-m",
            "vllm.entrypoints.openai.api_server",
            "--model",
            model,
            "--host",
            "0.0.0.0",
            "--port",
            str(VLLM_PORT),
        ]

        mapping = {
            "max_model_len": "--max-model-len",
            "gpu_memory_utilization": "--gpu-memory-utilization",
            "tensor_parallel_size": "--tensor-parallel-size",
            "dtype": "--dtype",
            "quantization": "--quantization",
            "max_num_batched_tokens": "--max-num-batched-tokens",
        }

        for key, flag in mapping.items():
            value = kwargs.get(key)
            if value is not None and value != "auto":
                cmd.extend([flag, str(value)])

        if kwargs.get("trust_remote_code"):
            cmd.append("--trust-remote-code")
        if kwargs.get("enable_prefix_caching"):
            cmd.append("--enable-prefix-caching")

        print(f"\n[LAUNCH] Starting vLLM server...")
        print(f"[LAUNCH] Model: {model}")
        print(f"[LAUNCH] Port: {VLLM_PORT}")
        print(f"[LAUNCH] {' '.join(cmd)}")

        creation_flags = 0
        if IS_WINDOWS:
            creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP

        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            creationflags=creation_flags,
        )

        self.pid = self.process.pid
        self.model = model
        self.args = kwargs
        self.start_time = time.time()
        self.is_running = True
        self.log_lines = []

        self._log_thread = threading.Thread(
            target=self._read_log_stream, args=(self.process.stdout,), daemon=True
        )
        self._log_thread.start()

        print(f"[OK] vLLM server started (PID: {self.pid})")

        return {
            "status": "started",
            "model": model,
            "pid": self.pid,
            "port": VLLM_PORT,
            "api_url": f"http://localhost:{VLLM_PORT}/v1",
            "docs_url": f"http://localhost:{VLLM_PORT}/docs",
        }

    def stop(self) -> Dict[str, Any]:
        """Terminate vLLM server and all child processes."""
        if not self.is_running or self.process is None:
            return {"status": "not_running"}

        print(f"[STOP] Stopping vLLM server (PID: {self.pid})...")

        try:
            if IS_WINDOWS:
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(self.pid)],
                    capture_output=True,
                    timeout=10,
                )
            else:
                parent = psutil.Process(self.pid)
                children = parent.children(recursive=True)
                parent.terminate()
                for child in children:
                    try:
                        child.terminate()
                    except Exception:
                        pass
                _, alive = psutil.wait_procs([parent] + children, timeout=5)
                for p in alive:
                    try:
                        p.kill()
                    except Exception:
                        pass

            self.process.wait(timeout=10)
        except Exception as exc:
            print(f"[WARN] Error during shutdown: {exc}")
            if self.process:
                try:
                    self.process.kill()
                except Exception:
                    pass

        self.is_running = False
        self.process = None
        self.pid = None
        self.model = None
        self.args = {}
        self.start_time = None

        print("[OK] vLLM server stopped")
        return {"status": "stopped"}

    # ------------------------------------------------------------------
    # Log handling
    # ------------------------------------------------------------------

    def _read_log_stream(self, stream) -> None:
        """Read lines from subprocess stdout in a background thread."""
        for line in iter(stream.readline, ""):
            stripped = line.rstrip()
            if stripped:
                with self.log_lock:
                    self.log_lines.append(stripped)
                    if len(self.log_lines) > LOG_MAX_LINES:
                        self.log_lines = self.log_lines[-LOG_MAX_LINES:]

    def get_logs(self, lines: int = 100) -> List[str]:
        """Return the most recent log lines."""
        with self.log_lock:
            return self.log_lines[-lines:]

    # ------------------------------------------------------------------
    # Process metrics
    # ------------------------------------------------------------------

    def get_process_metrics(self) -> Optional[Dict[str, Any]]:
        """Return CPU, memory, and thread info for the vLLM process."""
        if not self.is_running or not self.pid:
            return None

        try:
            proc = psutil.Process(self.pid)
            return {
                "cpu_percent": proc.cpu_percent(interval=0.1),
                "memory_rss": proc.memory_info().rss,
                "memory_vms": proc.memory_info().vms,
                "threads": proc.num_threads(),
                "status": proc.status(),
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return None


server_manager = VLLMServerManager()
