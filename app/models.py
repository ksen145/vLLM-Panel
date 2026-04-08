"""Pydantic request/response models."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class ServerStartRequest(BaseModel):
    model: str
    max_model_len: int = 4096
    gpu_memory_utilization: float = 0.9
    tensor_parallel_size: int = 1
    dtype: str = "auto"
    quantization: Optional[str] = None
    trust_remote_code: bool = False
    max_num_batched_tokens: Optional[int] = None
    enable_prefix_caching: bool = False


class ChatCompletionRequest(BaseModel):
    model: Optional[str] = None
    messages: List[Dict[str, str]]
    max_tokens: Optional[int] = None
    temperature: float = 0.7
    top_p: float = 1.0
    stream: bool = False
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[str] = None


class GenerateRequest(BaseModel):
    prompt: str
    max_tokens: int = 256
    temperature: float = 0.7
    top_p: float = 1.0


class ModelDownloadRequest(BaseModel):
    model_name: str
