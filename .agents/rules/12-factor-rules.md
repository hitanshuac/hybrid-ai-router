---
name: 12-Factor Governance
description: Enforces the 12-Factor App methodology for all AI-generated architectural changes.
---

# 12-Factor App Methodology

When generating code, scaffolding architecture, or debugging issues within this repository, you MUST adhere to the following principles. This repository is not a script; it is a **Production-Ready Agentic Environment**.

<factor_ruleset>
## Factor I: Codebase
- All architectural logic, including this very rule file, must be tracked in version control.
- Ensure the `.agents` folder is accurately updated when AI behavior needs to change globally.

<factor_ruleset>
## Factor III: Config
- **STRICT PROHIBITION**: You are strictly forbidden from hardcoding API keys, secrets, or environment-specific connection strings into the source code (`src/`).
- Use the **BYOK (Bring Your Own Keys)** strategy. Configuration must be injected dynamically via environment variables (`os.environ`), `.secrets/` text files, or the `.config/antigravity/project_settings.toml` manifest.

## Factor VI: Processes
- The application (e.g., FastAPI gateway) must execute **statelessly**. 
- The router should hold no memory of past requests. 
- Stateful persistence must be delegated to backing services (e.g., DuckDB telemetry, Parquet Dead-Letter Queues).

<factor_ruleset>
## Factor IX: Disposability
- Systems must gracefully handle sudden provider crashes.
- Do not let the main event loop freeze. 
- Rely on Circuit Breakers and Dead-Letter Queues (`data/quarantine_*.parquet`) to isolate faults and keep the system alive.

## Factor XI: Logs
- Treat logs as continuous event streams.
- Use lock-free background threadpools to push telemetry directly to the DuckDB metrics plane.
- Document immutable architectural decisions natively in `RETROSPECTIVE.md`.



</factor_ruleset>

