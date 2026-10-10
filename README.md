# Voice — AI-native messaging prototype

An Android-first messaging MVP where the assistant produces concise messages that match a user's communication style.

## Run the backend (unit-test / no-model mode)

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The backend now requires its own self-hosted inference service for all AI endpoints. It has no external-provider or hardcoded-response fallback. See [self-hosted AI operations](docs/self-hosted-ai.md) for controlled GPU deployment, model pinning, and local commands. Unit tests use a mock of that **internal** service and do not test model quality.

The Android debug app is configured to reach the backend at `http://10.0.2.2:8000/` (the emulator alias for the host machine). Its current UI remains an offline seeded prototype; server authentication/network wiring is the next Android client milestone.

The working prototype name is **Voice** because no product name was supplied; it can be changed through the Android label and Gradle project name.

## Android

Open the repository in Android Studio, sync Gradle, and run `app` on an API 26+ emulator/device. The first launch offers a brief onboarding; sample chats are immediately available.

## Architecture

- `app/`: Compose UI, local seeded messaging repository, AI/service interfaces, and interaction-led profile updates.
- `backend/`: FastAPI boundary with REST, authenticated prototype message delivery, WebSockets, and a private vLLM orchestration path.

Messages and AI prompts are never logged by the supplied code. The backend's in-memory repositories and prototype sessions are deliberately development-only; they must be replaced by PostgreSQL and production authentication before release.
