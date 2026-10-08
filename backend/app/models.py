from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class RelationshipType(StrEnum):
    CLOSE_FRIEND = "close_friend"
    FAMILY = "family"
    COLLEAGUE = "colleague"
    MANAGER = "manager"
    PARTNER = "partner"
    ACQUAINTANCE = "acquaintance"


class CommunicationProfile(BaseModel):
    preferred_message_length: Literal["short", "medium", "long"] = "short"
    capitalization: Literal["mostly_lowercase", "sentence_case", "mixed"] = "mostly_lowercase"
    emoji_frequency: Literal["low", "medium", "high"] = "high"
    common_emojis: list[str] = Field(default_factory=lambda: ["😂", "😭", "🤝"])
    language_style: str = "hinglish"
    preferred_tone: str = "casual"
    common_words: list[str] = Field(default_factory=lambda: ["bro", "yeah"])


class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    username: str
    display_name: str
    avatar: str | None = None
    preferred_language: str = "English"
    communication_profile: CommunicationProfile = Field(default_factory=CommunicationProfile)


class PrototypeSessionRequest(BaseModel):
    username: str = Field(min_length=2, max_length=32, pattern=r"^[a-zA-Z0-9_]+$")
    display_name: str = Field(min_length=1, max_length=80)
    preferred_language: str = Field(default="English", max_length=40)


class PrototypeSession(BaseModel):
    user: User
    # This is deliberately not a production credential. Replace the session service before release.
    session_id: str


class Message(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    conversation_id: str
    sender_id: str
    text: str = Field(min_length=1, max_length=4000)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "sent"


class Conversation(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    type: Literal["direct", "group"] = "direct"
    participant_ids: list[str]
    relationship_type: RelationshipType = RelationshipType.ACQUAINTANCE
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AiContext(BaseModel):
    conversation_id: str
    relationship_type: RelationshipType
    messages: list[Message] = Field(default_factory=list, max_length=25)
    profile: CommunicationProfile = Field(default_factory=CommunicationProfile)
    draft: str = Field(default="", max_length=4000)
    tone: str | None = None


class SuggestionsResponse(BaseModel):
    suggestions: list[str]


class TransformResponse(BaseModel):
    text: str


class StyleUpdate(BaseModel):
    selected_text: str = Field(min_length=1, max_length=4000)
    edited_text: str | None = Field(default=None, max_length=4000)
