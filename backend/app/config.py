"""Configuration for services operated inside our controlled environment."""
from __future__ import annotations

import os
from dataclasses import dataclass


def _bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    return default if value is None else value.strip().lower() in {"1", "true", "yes"}


def _positive_int(name: str, default: int) -> int:
    value = int(os.getenv(name, str(default)))
    if value < 1:
        raise ValueError(f"{name} must be positive")
    return value


@dataclass(frozen=True)
class Settings:
    inference_base_url: str
    inference_model_id: str
    inference_model_revision: str
    inference_timeout_seconds: int
    inference_max_concurrency: int
    ai_max_context_chars: int
    ai_max_generated_tokens: int
    ai_rate_limit_per_minute: int
    require_prototype_auth: bool
    inference_auth_token: str | None

    @classmethod
    def from_env(cls) -> "Settings":
        url = os.getenv("INFERENCE_BASE_URL", "http://localhost:8001/v1").rstrip("/")
        # This boundary is internal: public hosted inference endpoints are not allowed.
        if not (url.startswith("http://localhost") or url.startswith("http://127.0.0.1") or ".internal" in url or url.startswith("http://inference")):
            raise ValueError("INFERENCE_BASE_URL must resolve to a controlled internal service")
        return cls(
            inference_base_url=url,
            inference_model_id=os.getenv("INFERENCE_MODEL_ID", "Qwen/Qwen2.5-7B-Instruct"),
            inference_model_revision=os.getenv("INFERENCE_MODEL_REVISION", "a09a35458c702b33eeacc393d103063234e8bc28"),
            inference_timeout_seconds=_positive_int("INFERENCE_TIMEOUT_SECONDS", 30),
            inference_max_concurrency=_positive_int("INFERENCE_MAX_CONCURRENCY", 4),
            ai_max_context_chars=_positive_int("AI_MAX_CONTEXT_CHARS", 6000),
            ai_max_generated_tokens=_positive_int("AI_MAX_GENERATED_TOKENS", 160),
            ai_rate_limit_per_minute=_positive_int("AI_RATE_LIMIT_PER_MINUTE", 20),
            require_prototype_auth=_bool("REQUIRE_PROTOTYPE_AUTH", True),
            inference_auth_token=os.getenv("INFERENCE_AUTH_TOKEN") or None,
        )
