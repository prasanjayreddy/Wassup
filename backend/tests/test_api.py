from __future__ import annotations

import logging

from fastapi.testclient import TestClient

from app.config import Settings
from app.inference import InferenceTimedOut, InferenceUnavailable
from app.main import create_app
from app.security import SensitiveContentFilter


class FakeInference:
    def __init__(self, outputs: list[str] | None = None, error: Exception | None = None) -> None:
        self.outputs = outputs or ['["yeah bro", "can\'t make it", "what time?"]']
        self.error = error
        self.requests: list[dict] = []

    async def healthy(self) -> bool:
        return self.error is None

    async def complete(self, messages: list[dict[str, str]], *, max_tokens: int, temperature: float, n: int = 1) -> list[str]:
        self.requests.append({"messages": messages, "max_tokens": max_tokens, "temperature": temperature, "n": n})
        if self.error:
            raise self.error
        return self.outputs


def settings(**overrides) -> Settings:
    defaults = dict(
        inference_base_url="http://inference.internal/v1", inference_model_id="Qwen/Qwen2.5-7B-Instruct",
        inference_model_revision="test-revision", inference_timeout_seconds=2, inference_max_concurrency=2,
        ai_max_context_chars=100, ai_max_generated_tokens=80, ai_rate_limit_per_minute=20,
        require_prototype_auth=True, inference_auth_token=None,
    )
    defaults.update(overrides)
    return Settings(**defaults)


def new_user(client: TestClient, username: str) -> tuple[dict[str, str], str]:
    response = client.post("/auth/prototype/session", json={"username": username, "display_name": username})
    data = response.json()
    return {"X-Prototype-Session": data["session_id"]}, data["user"]["id"]


def conversation(client: TestClient, headers: dict[str, str], user_id: str) -> str:
    response = client.post("/conversations", headers=headers, json={"participant_ids": [user_id, "friend"], "relationship_type": "close_friend"})
    assert response.status_code == 201
    return response.json()["id"]


def context(conversation_id: str, **overrides) -> dict:
    value = {
        "conversation_id": conversation_id, "relationship_type": "close_friend",
        "messages": [{"conversation_id": conversation_id, "sender_id": "friend", "text": "bro are you coming tomorrow?"}],
        "profile": {"common_words": ["SHOULD_NOT_BE_USED"]},
        "draft": "I cannot come tomorrow because I have work",
    }
    value.update(overrides)
    return value


def test_ai_reply_uses_private_inference_and_server_scoped_profile() -> None:
    fake = FakeInference()
    client = TestClient(create_app(settings(), fake))
    headers, user_id = new_user(client, "aman")
    response = client.post("/ai/reply", headers=headers, json=context(conversation(client, headers, user_id)))
    assert response.status_code == 200
    assert response.json()["suggestions"] == ["yeah bro", "can't make it", "what time?"]
    rendered_prompt = fake.requests[0]["messages"][1]["content"]
    assert "SHOULD_NOT_BE_USED" not in rendered_prompt
    assert "bro are you coming tomorrow?" in rendered_prompt


def test_no_model_fallback_when_private_inference_is_unavailable() -> None:
    client = TestClient(create_app(settings(), FakeInference(error=InferenceUnavailable())))
    headers, user_id = new_user(client, "aman")
    response = client.post("/ai/reply", headers=headers, json=context(conversation(client, headers, user_id)))
    assert response.status_code == 503
    assert "unavailable" in response.json()["detail"].lower()


def test_timeout_is_reported_without_sensitive_echo() -> None:
    client = TestClient(create_app(settings(), FakeInference(error=InferenceTimedOut())))
    headers, user_id = new_user(client, "aman")
    response = client.post("/ai/rewrite", headers=headers, json=context(conversation(client, headers, user_id), draft="secret private draft"))
    assert response.status_code == 504
    assert "secret private draft" not in response.text


def test_message_and_websocket_delivery_require_membership() -> None:
    client = TestClient(create_app(settings(), FakeInference()))
    headers, user_id = new_user(client, "aman")
    conversation_id = conversation(client, headers, user_id)
    with client.websocket_connect(f"/ws/conversations/{conversation_id}", headers=headers) as socket:
        response = client.post("/messages", headers=headers, json={"conversation_id": conversation_id, "sender_id": user_id, "text": "hello"})
        assert response.status_code == 201
        assert socket.receive_json()["text"] == "hello"
    other_headers, _ = new_user(client, "other")
    assert client.get(f"/conversations/{conversation_id}/messages", headers=other_headers).status_code == 403


def test_style_updates_do_not_cross_user_profiles() -> None:
    fake = FakeInference()
    client = TestClient(create_app(settings(), fake))
    first_headers, first_id = new_user(client, "first")
    second_headers, second_id = new_user(client, "second")
    first_conversation = conversation(client, first_headers, first_id)
    second_conversation = conversation(client, second_headers, second_id)
    assert client.post("/ai/style/update", headers=first_headers, json={"selected_text": "legendary 😂"}).status_code == 204
    assert client.post("/ai/reply", headers=first_headers, json=context(first_conversation)).status_code == 200
    assert client.post("/ai/reply", headers=second_headers, json=context(second_conversation)).status_code == 200
    assert "legendary" in fake.requests[0]["messages"][1]["content"]
    assert "legendary" not in fake.requests[1]["messages"][1]["content"]


def test_context_limits_validation_and_log_filter() -> None:
    fake = FakeInference()
    client = TestClient(create_app(settings(ai_max_context_chars=35), fake))
    headers, user_id = new_user(client, "aman")
    conversation_id = conversation(client, headers, user_id)
    oversized = context(conversation_id, messages=[{"conversation_id": conversation_id, "sender_id": "friend", "text": "x" * 1000}])
    assert client.post("/ai/rewrite", headers=headers, json=oversized).status_code == 200
    assert len(fake.requests[0]["messages"][1]["content"]) < 1_000
    record = logging.LogRecord("test", logging.INFO, "", 0, "draft: private words", (), None)
    assert SensitiveContentFilter().filter(record)
    assert record.getMessage() == "Sensitive content redacted"
