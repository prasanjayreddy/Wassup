"""Prototype-only auth, authorization, rate limiting, and privacy-safe logging primitives."""
from __future__ import annotations

import logging
import secrets
import time
from collections import defaultdict, deque
from dataclasses import dataclass

from fastapi import HTTPException

from .models import CommunicationProfile, PrototypeSession, PrototypeSessionRequest, User


@dataclass(frozen=True)
class CurrentUser:
    user: User
    session_id: str


class PrototypeSessionStore:
    """In-memory only. Replace with verified tokens before production release."""
    def __init__(self) -> None:
        self._sessions: dict[str, User] = {}

    def create(self, request: PrototypeSessionRequest) -> PrototypeSession:
        user = User(username=request.username, display_name=request.display_name, preferred_language=request.preferred_language)
        session_id = secrets.token_urlsafe(32)
        self._sessions[session_id] = user
        return PrototypeSession(user=user, session_id=session_id)

    def current(self, session_id: str | None) -> CurrentUser:
        user = self._sessions.get(session_id or "")
        if not user:
            raise HTTPException(401, "Invalid or missing session")
        return CurrentUser(user=user, session_id=session_id or "")


class CommunicationProfileRepository:
    """Profiles are user-scoped. Raw interaction text is never stored here."""
    def __init__(self) -> None:
        self._profiles: dict[str, CommunicationProfile] = {}

    def get(self, user_id: str, default: CommunicationProfile) -> CommunicationProfile:
        return self._profiles.get(user_id, default)

    def update_from_interaction(self, user_id: str, event_text: str, default: CommunicationProfile) -> CommunicationProfile:
        previous = self.get(user_id, default)
        emoji_frequency = "high" if any(ord(char) > 10_000 for char in event_text) else previous.emoji_frequency
        token = next((word.lower().strip(".,!?") for word in event_text.split() if len(word) > 2), None)
        words = ([token] if token else []) + [word for word in previous.common_words if word != token]
        updated = previous.model_copy(update={"emoji_frequency": emoji_frequency, "common_words": words[:32]})
        self._profiles[user_id] = updated
        return updated


class ConversationMembership:
    def __init__(self) -> None:
        self._members: dict[str, set[str]] = {}

    def create(self, conversation_id: str, participant_ids: list[str]) -> None:
        self._members[conversation_id] = set(participant_ids)

    def require_member(self, conversation_id: str, user_id: str) -> None:
        if user_id not in self._members.get(conversation_id, set()):
            raise HTTPException(403, "You do not have access to this conversation")


class SlidingWindowRateLimiter:
    def __init__(self, limit: int, period_seconds: int = 60) -> None:
        self._limit, self._period = limit, period_seconds
        self._events: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str) -> None:
        now = time.monotonic()
        bucket = self._events[key]
        while bucket and bucket[0] <= now - self._period:
            bucket.popleft()
        if len(bucket) >= self._limit:
            raise HTTPException(429, "AI request limit reached; try again shortly")
        bucket.append(now)


class SensitiveContentFilter(logging.Filter):
    """Last-resort redaction for log calls that include known payload field names."""
    SENSITIVE = ("text", "draft", "messages", "profile", "prompt", "suggestion", "response")

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage().lower()
        if any(token in message for token in self.SENSITIVE):
            record.msg, record.args = "Sensitive content redacted", ()
        return True


def configure_safe_logging() -> None:
    logging.getLogger().addFilter(SensitiveContentFilter())
