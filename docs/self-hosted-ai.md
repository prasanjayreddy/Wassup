# Self-hosted AI operations

## Implemented boundary

The application backend calls only an internal vLLM service over the Docker network (or a controlled internal endpoint). It uses plain `httpx`, not an OpenAI or another hosted-provider SDK. The route shape is compatible with vLLM's chat-completions API; that compatibility is a wire format, not a dependency on an external provider.

`VllmInferenceClient` has no fallback provider. A connection failure returns `503`; a timeout returns `504`; malformed inference output returns `502`. The model server is not published by `docker-compose.yml`, so Android clients cannot reach it directly.

## Recommended first model

Use **Qwen/Qwen2.5-7B-Instruct**, revision `a09a35458c702b33eeacc393d103063234e8bc28`, with vLLM. Its published model card lists Apache-2.0 and documents vLLM use. It is a reasonable initial candidate for concise conversational generation and multilingual evaluation, but it is **not yet approved by our own Hindi/Telugu/Hinglish evaluation**. Test it against a consented, de-identified evaluation set before production use.

The pinned revision must be reviewed again before any model upgrade; model licenses, safety behavior, and quality are release criteria.

## Capacity and runtime choice

vLLM is the selected runtime because this service needs concurrent chat generation on controlled GPU infrastructure. This repository intentionally does not add a second inference runtime. A practical starting point is:

- NVIDIA GPU with **24 GB VRAM** for Qwen2.5-7B bf16 with useful KV-cache headroom and an 8K context cap.
- At least 32 GB system RAM and roughly 25 GB free disk for image, model cache, and operational headroom.
- CUDA-capable Docker host and NVIDIA Container Toolkit.

A 16 GB GPU may require tighter context, lower concurrency, or a separately evaluated quantized deployment. CPU-only and this Windows development environment were not validated for real inference. Model weights are intentionally not committed to Git.

## Local controlled deployment

1. Install Docker Engine / Docker Desktop with GPU support and NVIDIA Container Toolkit on a suitable host.
2. Copy `backend/.env.example` to an uncommitted `.env`, then set a long random `INFERENCE_AUTH_TOKEN`. Keep the model ID and revision pinned unless deliberately reviewed.
3. From the repository root, start the controlled model and application:

   ```powershell
   docker compose --profile gpu up --build
   ```

   On first intentional startup, vLLM downloads the pinned public model revision into the local Docker volume. This download transfers model weights only; conversation content is never sent to that source. For air-gapped production, pre-populate the cache through an approved artifact process, scan it, and run with outbound network denied.

4. Verify only from a trusted internal network:

   ```powershell
   curl http://localhost:8000/health
   curl http://localhost:8000/ai/health
   ```

5. Create a prototype session, create a conversation containing that session's user ID, and pass its session ID in `X-Prototype-Session` for message and AI routes. The Android prototype currently uses its local demo source; connecting it to this authenticated backend is a separate client integration step.

For backend-only development without a GPU, run unit tests with the mocked internal gateway; do not enable a fake production AI fallback.

## Privacy and security controls

- Prompts, messages, profiles, and generated text are not logged by application code. Error bodies are generic.
- AI context is capped, newest-first, and only sent to the internal model service.
- The backend uses an internal URL allow-list, timeout, concurrency semaphore, request limits, and optional backend-to-inference bearer token.
- Prototype sessions and memberships gate messages, WebSockets, AI actions, and profile updates. They are **not production authentication**: replace them with verified credentials, persistent sessions, database-backed conversation membership, and TLS/mTLS before deployment.
- Style updates derive bounded aggregate signals and discard the raw event after request handling. They remain in-memory today.
- This product does not provide end-to-end encryption. Server-side AI sees supplied plaintext context during inference.

Self-hosting does not remove all exposure: the controlled cloud/colo provider, database backup system, host operators, container registry, model artifact source, and any opted-in monitoring system remain potential subprocessors. Keep inference and database networks private, encrypt disks/backups, minimize administrative access, redact operational logs, set retention/deletion policies, and audit privileged access.

## Training is deliberately not active

`DisabledTrainingExampleSink` is the default. The consent endpoint records a policy version only; it does not export messages or create training rows. Before training, add a separate consented-data store with encryption, user deletion, retention limits, PII filtering, deduplication, dataset versioning, train/validation/test isolation, model-version tracking, and documented evaluation gates. Never copy production conversation tables into a training dataset.
