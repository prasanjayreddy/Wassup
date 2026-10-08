"""Development in-memory persistence; Repository is the explicit PostgreSQL migration seam."""
from __future__ import annotations

from collections import defaultdict
from typing import Protocol

from .models import Message


class MessageRepository(Protocol):
    def add(self, message: Message) -> Message: ...
    def list_for_conversation(self, conversation_id: str) -> list[Message]: ...


class InMemoryMessageRepository:
    def __init__(self) -> None:
        self._messages: dict[str, list[Message]] = defaultdict(list)

    def add(self, message: Message) -> Message:
        self._messages[message.conversation_id].append(message)
        return message

    def list_for_conversation(self, conversation_id: str) -> list[Message]:
        return self._messages[conversation_id].copy()
