# Voice — AI-native messaging prototype

An Android-first messaging MVP where the assistant produces concise messages that match a user's communication style.

## Run the backend

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The Android debug app is configured to reach the backend at `http://10.0.2.2:8000/` (the emulator alias for the host machine). The app intentionally has no AI key and works with its privacy-safe local fallback when the backend is unavailable.

The working prototype name is **Voice** because no product name was supplied; it can be changed through the Android label and Gradle project name.

## Android

Open the repository in Android Studio, sync Gradle, and run `app` on an API 26+ emulator/device. The first launch offers a brief onboarding; sample chats are immediately available.

## Architecture

- `app/`: Compose UI, local seeded messaging repository, AI/service interfaces, and interaction-led profile updates.
- `backend/`: FastAPI boundary with REST and WebSocket message delivery. `DeterministicAiProvider` makes the demo work without third-party credentials; swap in an OpenAI-compatible provider through the `AiProvider` protocol.

Messages and AI prompts are never logged by the supplied code. The backend's in-memory repository is deliberately development-only; the repository interfaces are the migration seam for PostgreSQL.
