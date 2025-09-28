from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import httpx

from ..config import get_settings

OLLAMA_CHAT_PATH = "/api/chat"


class OllamaError(RuntimeError):
    """Raised when the Ollama API returns an error response."""


def _build_messages(messages: List[Dict[str, str]], system: Optional[str]) -> List[Dict[str, str]]:
    if system:
        return [{"role": "system", "content": system}, *messages]
    return messages


def _extract_message(payload: Dict[str, Any]) -> Dict[str, Any]:
    message = payload.get("message")
    if isinstance(message, dict):
        return message

    messages = payload.get("messages")
    if isinstance(messages, list) and messages:
        last = messages[-1]
        if isinstance(last, dict):
            return last

    raise OllamaError("Ollama response missing message content")


def _normalize_response(payload: Dict[str, Any]) -> Dict[str, Any]:
    message = _extract_message(payload)

    normalized_message: Dict[str, Any] = {
        "role": message.get("role", "assistant"),
        "content": message.get("content", ""),
    }

    tool_calls = message.get("tool_calls")
    if isinstance(tool_calls, list) and tool_calls:
        normalized_message["tool_calls"] = tool_calls

    return {
        "choices": [{"message": normalized_message}],
        "model": payload.get("model"),
        "created_at": payload.get("created_at"),
        "raw_response": payload,
    }


async def request_chat_completion(
    *,
    model: str,
    messages: List[Dict[str, str]],
    system: Optional[str] = None,
    api_key: Optional[str] = None,
    tools: Optional[List[Dict[str, Any]]] = None,
    base_url: Optional[str] = None,
) -> Dict[str, Any]:
    """Request a chat completion from a local Ollama instance."""

    settings = get_settings()
    host = (base_url or settings.ollama_host or "").strip()
    if not host:
        raise OllamaError("Ollama host not configured. Set OLLAMA_HOST environment variable.")

    payload: Dict[str, Any] = {
        "model": model,
        "messages": _build_messages(messages, system),
        "stream": False,
    }

    if tools:
        payload["tools"] = tools

    url = f"{host.rstrip('/')}{OLLAMA_CHAT_PATH}"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload, timeout=60.0)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text
            try:
                detail_json = exc.response.json()
                detail = json.dumps(detail_json)
            except Exception:
                pass
            raise OllamaError(
                f"Ollama request failed ({exc.response.status_code}): {detail}"
            ) from exc
        except httpx.HTTPError as exc:
            raise OllamaError(f"Ollama request failed: {exc}") from exc

    try:
        data = response.json()
    except json.JSONDecodeError as exc:
        raise OllamaError("Ollama response was not valid JSON") from exc

    return _normalize_response(data)


__all__ = ["OllamaError", "request_chat_completion", "OLLAMA_CHAT_PATH"]
