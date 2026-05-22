# Workspace Handover Context

## Current Secure Checkpoint
We are at the **v3.0.0 Stable Release** on the `main` branch. 
The workspace has just been successfully pushed to GitHub as a secure checkpoint (`[Safe Checkpoint] docs: sync v3.0.0 showcase documentation and SRE assets`).

### System State & Clarifications for Next Session
1. **AWS Bedrock**: AWS Bedrock is **not** present in the active 9-tier cascade. It was used in an older iteration (v2.x) and is only mentioned in `retrospective.md` as historical context regarding past failures and migrations. The active 9 tiers in `src/router.py` strictly use Groq, AI Studio (Gemini), OpenRouter, and NVIDIA NIM.
2. **API Keys & Evals**: The `eval_baseline.py` script ran successfully *without* real API keys because it uses **monkeypatching**. The script intercepts `httpx.post` network requests and returns simulated JSON responses (both successes and HTTP errors) to mathematically verify the router's fallback logic and circuit breaker behavior without ever hitting the real endpoints or costing credits. 

## Established Baseline (v3.0.0)
The active workspace features:
1. **9-Tier Cloud Cascade Engine**: Pure cloud API routing via `httpx`, zero local dependencies.
2. **SRE Guardrails**: Fully functioning `circuit_breaker.py` with 3-strike fault tolerance and O(1) context overflow routing.
3. **Open WebUI Integration**: A dedicated Hugging Face Docker Space (`HitanshuAC/Hybrid-Router-WebUI`) successfully decoupled from Ollama, securely authenticating via Space Secrets, and parsing fallback upstream models via the `/v1/models` mock endpoint.
4. **Docs & Assets**: Dual-presentation architecture diagrams and GitHub showcases are fully synchronized.

You are safe to initialize a new Antigravity workspace using this checkpoint. All codebase changes are pushed, secured, and validated.
