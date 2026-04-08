"""Chat completions and text generation proxy endpoints."""

import json
from typing import Any, Dict

import urllib.request
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.config import VLLM_PORT
from app.models import ChatCompletionRequest, GenerateRequest
from app.server_manager import server_manager

router = APIRouter()


@router.post("/api/chat/completions")
async def chat_completions(req: ChatCompletionRequest):
    target_url = f"http://localhost:{VLLM_PORT}/v1/chat/completions"
    payload: Dict[str, Any] = {
        "model": req.model or server_manager.model or "",
        "messages": req.messages,
        "max_tokens": req.max_tokens,
        "temperature": req.temperature,
        "top_p": req.top_p,
        "stream": req.stream,
    }
    if req.tools:
        payload["tools"] = req.tools
    if req.tool_choice:
        payload["tool_choice"] = req.tool_choice

    if req.stream:

        async def stream_response():
            data = json.dumps(payload).encode("utf-8")
            http_req = urllib.request.Request(
                target_url, data=data, headers={"Content-Type": "application/json"}
            )
            try:
                with urllib.request.urlopen(http_req, timeout=300) as resp:
                    for line in resp:
                        yield line.decode("utf-8")
            except Exception as exc:
                yield f'data: {{"error": "{str(exc)}"}}\n\n'

        return StreamingResponse(stream_response(), media_type="text/event-stream")

    data = json.dumps(payload).encode("utf-8")
    http_req = urllib.request.Request(
        target_url, data=data, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(http_req, timeout=300) as resp:
            result = resp.read().decode("utf-8")
        return json.loads(result)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"vLLM API error: {str(exc)}")


@router.post("/api/generate")
async def generate(req: GenerateRequest):
    target_url = f"http://localhost:{VLLM_PORT}/v1/completions"
    payload = {
        "model": server_manager.model or "",
        "prompt": req.prompt,
        "max_tokens": req.max_tokens,
        "temperature": req.temperature,
        "top_p": req.top_p,
    }

    data = json.dumps(payload).encode("utf-8")
    http_req = urllib.request.Request(
        target_url, data=data, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(http_req, timeout=300) as resp:
            result = resp.read().decode("utf-8")
        return json.loads(result)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"vLLM API error: {str(exc)}")
