# Prototype architecture

## Client

The Android client owns rendering, draft editing, and an offline-first seeded data source. `MessagingRepository` is deliberately narrow: its local implementation powers development and can be replaced by an HTTP/WebSocket implementation without changing Compose screens. `AiAssistant` follows the same pattern; `LocalAiAssistant` makes every AI interaction demonstrable while the backend is unavailable. It uses the saved profile’s emoji and capitalization preferences, while the backend receives the whole aggregate for future provider logic.

The client sends no provider credentials. When a backend implementation is enabled, it sends the smallest relevant context (recent messages, relationship, profile aggregate, action, draft/tone) to it over TLS.

## Service

FastAPI exposes message REST endpoints and one WebSocket per conversation. Connected clients receive each saved message. The in-memory repository is only for local development. Its `MessageRepository` protocol is the intentionally small migration point for PostgreSQL.

`AiProvider` is the corresponding model-provider seam. The supplied deterministic provider supports the seeded Rahul flow exactly and keeps tests/demo development independent of a hosted model. A production provider should build a request with `STYLE_SYSTEM_PROMPT`, use environment-only credentials, and return only validated message text.

## Data and privacy boundary

```
Android app ── minimal context ──> FastAPI ── provider request ──> LLM provider
       │                              │
       └ local profile aggregates      └ no request/message logging
```

Raw AI prompts are not stored. Style update events should produce aggregate preferences (length, capitalization, emoji use, language/tone) rather than store raw messages. Future work can add user deletion, retention policies, encryption, and local-only style learning behind the same interfaces.
