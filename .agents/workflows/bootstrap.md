---
name: Local Bootstrapper
description: Workflow to scaffold and verify the local environment before execution.
---

# Bootstrap Workflow

When initiating the workspace or onboarding a new developer/agent, execute these steps sequentially to ensure the 12-Factor App methodology is satisfied locally.

<workflow_steps>
1. **Verify Factor I (Codebase)**
   Ensure the repository is fully cloned and the `.agents` folder is intact.
   
2. **Verify Factor III (Config)**
   - Check if `.secrets` exists. If not, generate it.
   - Run a search for leaked API keys inside `src/`. If any are found, immediately purge them and move them to `.secrets`.
   - Ensure `.gitignore` is active and blocking `.secrets/`, `.env`, and `data/`.

3. **Verify Factor VI (Processes)**
   - Start the ASGI server (e.g., `uvicorn src.server:app`).
   - Validate that the router accepts stateless requests and successfully pushes telemetry via lock-free queues.

4. **Verify Factor XI (Logs)**
   - Ensure the `data/` directory exists (with `.gitkeep`).
   - Confirm `pipeline_metrics.db` is being generated and that Parquet files populate inside `data/quarantine_*` on failure.



</workflow_steps>

