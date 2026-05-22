# Fork Handover: Upgrading to v3.0.0 Baseline

This document provides the exact replication steps required to upgrade your two v2.4 forks (**Image AI Router** and **Terminal Based AI Router**) to the current **v3.0.0 SRE Baseline**.

To achieve parity with the `main` stable branch, you must implement the following architectural changes in both forks:

## 1. Implement SRE Circuit Breaker (`src/circuit_breaker.py`)
- **Action**: Create the `circuit_breaker.py` module.
- **Details**: Implement the "Centipede Guardrail". This includes:
  - Token estimation pre-flight heuristic (`len(prompt) // 4`).
  - A 3-strike fault-tolerance memory dictionary that tracks consecutive `HTTP 429`/`500` errors per tier.
  - A 300-second (5-minute) cooldown mechanism for tripped circuits.
  - **Purpose**: Prevents network retry storms and massive token payload rejections.

## 2. Upgrade the Cascade Engine (`src/router.py`)
- **Action**: Migrate to the 9-Tier Cloud Cascade.
- **Details**: 
  - Remove all local Ollama routing logic and dependencies.
  - Integrate the `circuit_breaker.py` functions: Call `is_circuit_open()` before attempting a tier, and use `record_success()` / `record_failure()` based on the HTTP response.
  - Ensure the fallback waterfall relies entirely on `httpx.AsyncClient` targeting Groq, AI Studio (Gemini), OpenRouter, and NVIDIA NIM.

## 3. Harden the API Server (`src/server.py`)
- **Action**: Implement Global SRE Guardrails.
- **Details**:
  - **Global Exception Handler**: Add `@app.exception_handler(Exception)` to catch all unhandled backend crashes. Return a structured `JSONResponse` with a 500 status code instead of letting FastAPI leak raw stack traces to your clients.
  - **Upstream Validation Mocking**: Add a `GET /v1/models` endpoint that returns a static JSON array containing the `hybrid-router` model.
  - **Purpose**: Prevents strict downstream clients (like Open WebUI or Terminal CLIs) from crashing when they attempt to fetch available models and unexpectedly receive a `404 Not Found` HTML page.

## 4. Frontend & Container Environment Fixes
- **Action**: Neutralize Aggressive DNS Polling.
- **Details**: 
  - If your forks use Open WebUI or similar Dockerized frontends, explicitly inject the environment variable `ENABLE_OLLAMA_API="False"`.
  - **Purpose**: Prevents the frontend from infinitely retrying `host.docker.internal:11434`, which causes catastrophic DNS resolution logs and memory leaks in ephemeral cloud environments like Hugging Face Spaces.
  - Ensure API keys are injected via secure Space Secrets or `.env` files, never hardcoded in the `Dockerfile`.

## 5. Deprecate Outdated Modules
- **Action**: Clean up legacy code.
- **Details**: Delete `src/bot.py` and any legacy Telegram polling logic if the router is strictly acting as an API gateway.

## Summary Checklist for Forks
- [ ] Copy `src/circuit_breaker.py` from `main` to the fork.
- [ ] Sync `src/router.py` to use the 9-tier cascade and circuit breaker logic.
- [ ] Sync `src/server.py` to include the `/v1/models` endpoint and global `500` exception handler.
- [ ] Update frontend `Dockerfile` / `docker-compose.yml` to disable Ollama API connections.
- [ ] Run `eval_baseline.py` (using monkeypatching) to verify cascade integrity.
