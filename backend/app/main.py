from __future__ import annotations

from collections import defaultdict
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect

from .ai import AiProvider, DeterministicAiProvider
from .models import AiContext, Message, PrototypeSession, PrototypeSessionRequest, StyleUpdate, SuggestionsResponse, TransformResponse, User
from .repository import InMemoryMessageRepository

app = FastAPI(title="Voice API", version="0.1.0")
messages = InMemoryMessageRepository()
ai: AiProvider = DeterministicAiProvider()
subscribers: dict[str, set[WebSocket]] = defaultdict(set)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/auth/prototype/session", response_model=PrototypeSession, status_code=201)
async def create_prototype_session(request: PrototypeSessionRequest) -> PrototypeSession:
    """MVP identity only; do not treat the returned value as an authentication token."""
    user = User(username=request.username, display_name=request.display_name, preferred_language=request.preferred_language)
    return PrototypeSession(user=user, session_id=f"prototype-{user.id}")


@app.get("/conversations/{conversation_id}/messages", response_model=list[Message])
async def list_messages(conversation_id: str) -> list[Message]:
    return messages.list_for_conversation(conversation_id)


@app.post("/messages", response_model=Message, status_code=201)
async def create_message(message: Message) -> Message:
    saved = messages.add(message)
    # Send to active clients only; nothing is logged here.
    stale: list[WebSocket] = []
    for socket in subscribers[saved.conversation_id]:
        try:
            await socket.send_json(saved.model_dump(mode="json"))
        except Exception:
            stale.append(socket)
    for socket in stale:
        subscribers[saved.conversation_id].discard(socket)
    return saved


@app.websocket("/ws/conversations/{conversation_id}")
async def conversation_socket(websocket: WebSocket, conversation_id: str) -> None:
    await websocket.accept()
    subscribers[conversation_id].add(websocket)
    try:
        while True:
            payload = await websocket.receive_json()
            message = Message.model_validate({**payload, "conversation_id": conversation_id})
            await create_message(message)
    except WebSocketDisconnect:
        subscribers[conversation_id].discard(websocket)


@app.post("/ai/reply", response_model=SuggestionsResponse)
async def ai_reply(context: AiContext) -> SuggestionsResponse:
    return SuggestionsResponse(suggestions=await ai.reply(context))


@app.post("/ai/rewrite", response_model=TransformResponse)
async def ai_rewrite(context: AiContext) -> TransformResponse:
    if not context.draft.strip():
        raise HTTPException(422, "A draft is required")
    return TransformResponse(text=await ai.rewrite(context))


@app.post("/ai/tone", response_model=TransformResponse)
async def ai_tone(context: AiContext) -> TransformResponse:
    if not context.draft.strip() or not context.tone:
        raise HTTPException(422, "A draft and tone are required")
    return TransformResponse(text=await ai.tone(context))


@app.post("/ai/translate", response_model=TransformResponse)
async def ai_translate(context: AiContext) -> TransformResponse:
    if not context.draft.strip():
        raise HTTPException(422, "A thought is required")
    return TransformResponse(text=await ai.translate(context))


@app.post("/ai/style/update", status_code=204)
async def update_style(event: StyleUpdate) -> None:
    # In a PostgreSQL implementation, derive aggregate style features here.
    # Do not persist raw prompt text or full conversation context by default.
    return None
