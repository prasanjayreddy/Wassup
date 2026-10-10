from __future__ import annotations

from collections import defaultdict
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from .ai import AiOrchestrator
from .config import Settings
from .inference import InferenceGateway, InferenceProtocolError, InferenceTimedOut, InferenceUnavailable, VllmInferenceClient
from .models import AiContext, Conversation, ConversationCreate, Message, PrototypeSession, PrototypeSessionRequest, StyleUpdate, SuggestionsResponse, TrainingConsentUpdate, TransformResponse
from .repository import InMemoryMessageRepository
from .security import CommunicationProfileRepository, ConversationMembership, CurrentUser, PrototypeSessionStore, SlidingWindowRateLimiter, configure_safe_logging


def create_app(settings: Settings | None = None, inference: InferenceGateway | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    configure_safe_logging()
    app = FastAPI(title="Voice API", version="0.2.0")
    messages = InMemoryMessageRepository()
    sessions = PrototypeSessionStore()
    profiles = CommunicationProfileRepository()
    membership = ConversationMembership()
    rate_limiter = SlidingWindowRateLimiter(settings.ai_rate_limit_per_minute)
    ai = AiOrchestrator(inference or VllmInferenceClient(settings), settings)
    subscribers: dict[str, set[WebSocket]] = defaultdict(set)
    training_consents: dict[str, str] = {}

    def current_user(x_prototype_session: Annotated[str | None, Header()] = None) -> CurrentUser:
        if not settings.require_prototype_auth:
            # This remains intentionally inconvenient: an unauthenticated production deployment is not supported.
            raise HTTPException(503, "Authentication must be enabled")
        return sessions.current(x_prototype_session)

    def scoped_context(context: AiContext, user: CurrentUser) -> AiContext:
        membership.require_member(context.conversation_id, user.user.id)
        if any(message.conversation_id != context.conversation_id for message in context.messages):
            raise HTTPException(422, "Context messages must belong to the requested conversation")
        # Never accept another user's profile from the client. Client-supplied profile is compatibility-only.
        profile = profiles.get(user.user.id, user.user.communication_profile)
        return context.model_copy(update={"profile": profile})

    async def publish(saved: Message) -> None:
        stale: list[WebSocket] = []
        for socket in subscribers[saved.conversation_id]:
            try:
                await socket.send_json(saved.model_dump(mode="json"))
            except Exception:
                stale.append(socket)
        for socket in stale:
            subscribers[saved.conversation_id].discard(socket)

    @app.exception_handler(InferenceUnavailable)
    async def unavailable_handler(_, __: InferenceUnavailable) -> JSONResponse:
        return JSONResponse(status_code=503, content={"detail": "Private inference service is unavailable"})

    @app.exception_handler(InferenceTimedOut)
    async def timeout_handler(_, __: InferenceTimedOut) -> JSONResponse:
        return JSONResponse(status_code=504, content={"detail": "Private inference service timed out"})

    @app.exception_handler(InferenceProtocolError)
    async def protocol_handler(_, __: InferenceProtocolError) -> JSONResponse:
        return JSONResponse(status_code=502, content={"detail": "Private inference returned an invalid response"})

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/ai/health")
    async def ai_health() -> Response:
        if await ai.gateway.healthy():
            return JSONResponse({"status": "ready", "runtime": "self-hosted-vllm"})
        return JSONResponse(status_code=503, content={"status": "unavailable", "runtime": "self-hosted-vllm"})

    @app.post("/auth/prototype/session", response_model=PrototypeSession, status_code=201)
    async def create_prototype_session(request: PrototypeSessionRequest) -> PrototypeSession:
        """Development identity only; replace with verified authentication before production."""
        return sessions.create(request)

    @app.post("/conversations", response_model=Conversation, status_code=201)
    async def create_conversation(request: ConversationCreate, user: CurrentUser = Depends(current_user)) -> Conversation:
        if user.user.id not in request.participant_ids:
            raise HTTPException(403, "The current user must be a conversation participant")
        conversation = Conversation(participant_ids=list(dict.fromkeys(request.participant_ids)), relationship_type=request.relationship_type)
        membership.create(conversation.id, conversation.participant_ids)
        return conversation

    @app.get("/conversations/{conversation_id}/messages", response_model=list[Message])
    async def list_messages(conversation_id: str, user: CurrentUser = Depends(current_user)) -> list[Message]:
        membership.require_member(conversation_id, user.user.id)
        return messages.list_for_conversation(conversation_id)

    @app.post("/messages", response_model=Message, status_code=201)
    async def create_message(message: Message, user: CurrentUser = Depends(current_user)) -> Message:
        membership.require_member(message.conversation_id, user.user.id)
        if message.sender_id != user.user.id:
            raise HTTPException(403, "A message sender must match the authenticated user")
        saved = messages.add(message)
        await publish(saved)
        return saved

    @app.websocket("/ws/conversations/{conversation_id}")
    async def conversation_socket(websocket: WebSocket, conversation_id: str) -> None:
        try:
            user = sessions.current(websocket.headers.get("x-prototype-session"))
            membership.require_member(conversation_id, user.user.id)
        except HTTPException:
            await websocket.close(code=1008)
            return
        await websocket.accept()
        subscribers[conversation_id].add(websocket)
        try:
            while True:
                payload = await websocket.receive_json()
                message = Message.model_validate({**payload, "conversation_id": conversation_id})
                if message.sender_id != user.user.id:
                    await websocket.close(code=1008)
                    return
                saved = messages.add(message)
                await publish(saved)
        except WebSocketDisconnect:
            subscribers[conversation_id].discard(websocket)

    async def run_ai(action: str, context: AiContext, user: CurrentUser):
        rate_limiter.check(user.user.id)
        context = scoped_context(context, user)
        return await getattr(ai, action)(context)

    @app.post("/ai/reply", response_model=SuggestionsResponse)
    async def ai_reply(context: AiContext, user: CurrentUser = Depends(current_user)) -> SuggestionsResponse:
        return SuggestionsResponse(suggestions=await run_ai("reply", context, user))

    @app.post("/ai/rewrite", response_model=TransformResponse)
    async def ai_rewrite(context: AiContext, user: CurrentUser = Depends(current_user)) -> TransformResponse:
        if not context.draft.strip():
            raise HTTPException(422, "A draft is required")
        return TransformResponse(text=await run_ai("rewrite", context, user))

    @app.post("/ai/tone", response_model=TransformResponse)
    async def ai_tone(context: AiContext, user: CurrentUser = Depends(current_user)) -> TransformResponse:
        if not context.draft.strip() or not context.tone:
            raise HTTPException(422, "A draft and tone are required")
        return TransformResponse(text=await run_ai("tone", context, user))

    @app.post("/ai/translate", response_model=TransformResponse)
    async def ai_translate(context: AiContext, user: CurrentUser = Depends(current_user)) -> TransformResponse:
        if not context.draft.strip():
            raise HTTPException(422, "A thought is required")
        return TransformResponse(text=await run_ai("translate", context, user))

    @app.post("/ai/style/update", status_code=204)
    async def update_style(event: StyleUpdate, user: CurrentUser = Depends(current_user)) -> Response:
        profiles.update_from_interaction(user.user.id, event.edited_text or event.selected_text, user.user.communication_profile)
        return Response(status_code=204)

    @app.put("/privacy/training-consent", status_code=204)
    async def update_training_consent(consent: TrainingConsentUpdate, user: CurrentUser = Depends(current_user)) -> Response:
        if consent.enabled:
            training_consents[user.user.id] = consent.policy_version
        else:
            training_consents.pop(user.user.id, None)
        # Consent is recorded only. No raw messages, suggestions, or dataset records are collected yet.
        return Response(status_code=204)

    return app


app = create_app()
