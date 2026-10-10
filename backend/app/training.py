"""Future training boundary. Production conversation storage must never feed this automatically."""
from __future__ import annotations

from typing import Protocol


class TrainingExampleSink(Protocol):
    async def record_opted_in_example(self, *, user_id: str, task: str, generated: str, edited: str | None) -> None: ...


class DisabledTrainingExampleSink:
    """Default implementation: consent alone never exports or stores a training example."""
    async def record_opted_in_example(self, *, user_id: str, task: str, generated: str, edited: str | None) -> None:
        return None
