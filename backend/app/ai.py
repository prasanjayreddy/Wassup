"""LLM boundary. Do not log prompts or messages in this layer."""
from __future__ import annotations

from typing import Protocol

from .models import AiContext, RelationshipType


STYLE_SYSTEM_PROMPT = """Write like the user, not an AI assistant. Return only the message.
Keep it concise and natural. Match their vocabulary, punctuation, capitalization, emoji
habits and language mix. Use relationship context. Avoid corporate language, generic
politeness, explanations, excessive punctuation, and unnecessary emojis."""


class AiProvider(Protocol):
    async def reply(self, context: AiContext) -> list[str]: ...
    async def rewrite(self, context: AiContext) -> str: ...
    async def tone(self, context: AiContext) -> str: ...
    async def translate(self, context: AiContext) -> str: ...


class DeterministicAiProvider:
    """Safe development provider. Replace with an OpenAI-compatible provider via this protocol."""
    async def reply(self, context: AiContext) -> list[str]:
        if context.relationship_type == RelationshipType.CLOSE_FRIEND:
            return ["yeah bro I'll be there 😂", "can't make it tomorrow bro, got some work", "what time are you guys meeting?"]
        if context.relationship_type in {RelationshipType.COLLEAGUE, RelationshipType.MANAGER}:
            return ["Yep, I’ll send it shortly.", "Almost done — I’ll share it in a bit.", "I’m on it, will update you soon."]
        if context.relationship_type == RelationshipType.FAMILY:
            return ["on my way, will be home soon", "yeah coming in a bit", "sorry, got held up — leaving now"]
        return ["yeah, sounds good", "I might be a little late", "what time works for you?"]

    async def rewrite(self, context: AiContext) -> str:
        text = context.draft.lower().strip()
        if "cannot come tomorrow" in text or "can't come tomorrow" in text:
            return "can't make it tomorrow bro, got some work" if context.relationship_type == RelationshipType.CLOSE_FRIEND else "I can't make it tomorrow, I have some work."
        return context.draft.strip()

    async def tone(self, context: AiContext) -> str:
        rewritten = await self.rewrite(context)
        if context.tone == "professional":
            return rewritten.replace("bro", "").replace("😂", "").strip().capitalize()
        if context.tone == "funny":
            return f"{rewritten} 😂"
        if context.tone == "short":
            return rewritten.split(",")[0]
        return rewritten

    async def translate(self, context: AiContext) -> str:
        thought = context.draft.lower()
        if "repu" in thought and "late" in thought:
            return "bro I'll be a little late tomorrow, there's a lot of traffic"
        if "kal" in thought and "late" in thought:
            return "I'll be a little late tomorrow, there's a lot of traffic"
        return context.draft.strip()
