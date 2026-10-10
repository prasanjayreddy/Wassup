"""Minimal client for our private vLLM deployment; it has no hosted-provider fallback."""
from __future__ import annotations

import asyncio
from typing import Protocol

import httpx

from .config import Settings


class InferenceUnavailable(Exception):
    pass


class InferenceTimedOut(Exception):
    pass


class InferenceProtocolError(Exception):
    pass


class InferenceGateway(Protocol):
    async def complete(self, messages: list[dict[str, str]], *, max_tokens: int, temperature: float, n: int = 1) -> list[str]: ...
    async def healthy(self) -> bool: ...


class VllmInferenceClient:
    """Calls an internal vLLM OpenAI-compatible endpoint without using an external SDK."""
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._semaphore = asyncio.Semaphore(settings.inference_max_concurrency)

    @property
    def _headers(self) -> dict[str, str]:
        if not self._settings.inference_auth_token:
            return {}
        return {"Authorization": f"Bearer {self._settings.inference_auth_token}"}

    async def healthy(self) -> bool:
        try:
            timeout = httpx.Timeout(self._settings.inference_timeout_seconds)
            async with httpx.AsyncClient(timeout=timeout, headers=self._headers) as client:
                response = await client.get(f"{self._settings.inference_base_url}/models")
                return response.status_code == 200
        except httpx.HTTPError:
            return False

    async def complete(self, messages: list[dict[str, str]], *, max_tokens: int, temperature: float, n: int = 1) -> list[str]:
        payload = {
            "model": self._settings.inference_model_id,
            "messages": messages,
            "max_tokens": min(max_tokens, self._settings.ai_max_generated_tokens),
            "temperature": temperature,
            "n": n,
        }
        try:
            async with self._semaphore:
                timeout = httpx.Timeout(self._settings.inference_timeout_seconds)
                async with httpx.AsyncClient(timeout=timeout, headers=self._headers) as client:
                    response = await client.post(f"{self._settings.inference_base_url}/chat/completions", json=payload)
        except httpx.TimeoutException as exc:
            raise InferenceTimedOut("private inference timed out") from exc
        except httpx.HTTPError as exc:
            raise InferenceUnavailable("private inference is unavailable") from exc
        if response.status_code in {408, 504}:
            raise InferenceTimedOut("private inference timed out")
        if response.status_code >= 500:
            raise InferenceUnavailable("private inference is unavailable")
        if response.status_code >= 400:
            raise InferenceProtocolError("private inference rejected the request")
        try:
            choices = response.json()["choices"]
            texts = [choice["message"]["content"].strip() for choice in choices]
        except (KeyError, TypeError, ValueError) as exc:
            raise InferenceProtocolError("private inference returned an invalid response") from exc
        if not texts or any(not text for text in texts):
            raise InferenceProtocolError("private inference returned no usable text")
        return texts
