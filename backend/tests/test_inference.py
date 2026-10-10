from __future__ import annotations

import asyncio

import httpx
import pytest

from app.config import Settings
from app.inference import InferenceProtocolError, VllmInferenceClient


def settings() -> Settings:
    return Settings("http://inference.internal/v1", "test-model", "test-revision", 2, 1, 100, 50, 10, True, None)


def test_internal_vllm_response_is_parsed(monkeypatch) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "inference.internal"
        assert request.url.path == "/v1/chat/completions"
        return httpx.Response(200, json={"choices": [{"message": {"content": "hi"}}]})

    original = httpx.AsyncClient
    class MockClient(original):
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = httpx.MockTransport(handler)
            super().__init__(*args, **kwargs)
    monkeypatch.setattr("app.inference.httpx.AsyncClient", MockClient)
    output = asyncio.run(VllmInferenceClient(settings()).complete([{"role": "user", "content": "hello"}], max_tokens=10, temperature=0.1))
    assert output == ["hi"]


def test_malformed_model_response_is_rejected(monkeypatch) -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": []})

    original = httpx.AsyncClient
    class MockClient(original):
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = httpx.MockTransport(handler)
            super().__init__(*args, **kwargs)
    monkeypatch.setattr("app.inference.httpx.AsyncClient", MockClient)
    with pytest.raises(InferenceProtocolError):
        asyncio.run(VllmInferenceClient(settings()).complete([{"role": "user", "content": "hello"}], max_tokens=10, temperature=0.1))
