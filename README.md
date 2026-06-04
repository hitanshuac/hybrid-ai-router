# 🌌 Antigravity Base Agentic Environment

![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=flat&logo=fastapi)
![DuckDB](https://img.shields.io/badge/DuckDB-FFF000?style=flat&logo=duckdb&logoColor=black)
![Architecture](https://img.shields.io/badge/Architecture-Split--Plane-indigo)

## 📖 Overview
This repository serves as a powerful, extensible **Base Agentic Environment** built on the Antigravity framework. It utilizes a strict **Split-Plane Architecture** that separates the human-defined control plane (`.agents/`) from the system-managed data and state plane (`.antigravity/`). This ensures deterministic AI execution, zero-hallucination context management, and enterprise-grade reliability.

## 🚀 Dynamic Skill Integration
This workspace is designed to be highly composable. **As new skills and agents are developed in separate, isolated projects, they are continuously imported into this base environment.** This aggregation allows the environment to grow exponentially more powerful over time, consolidating isolated intelligence into a single, unified operating system.

## 🛠️ Current Capabilities

### Governance Rules (`.agents/rules/`)
* **12-Factor Governance:** Enforces stateless processes and BYOK configuration.
* **Context Compaction & Router Alignment:** Strict token conservation and payload mutation for Hybrid AI.
* **Data Validation:** Idempotent DLQ routing via Pydantic.
* **SQL Standards:** Write-Ahead Logging and `INSERT OR REPLACE` idempotency via DuckDB.
* **Hugging Face Standards:** Zero-cost offsite WebUI routing deployment constraints.

### Specialized Skills (`.agents/skills/`)
* **DuckDB Optimizer:** Configures DuckDB for maximum reliability, data integrity, and memory safety.
* **Pipeline Architect:** Designs minimalist, fault-tolerant ETL pipelines using standard Python.

### Automated Workflows (`.agents/workflows/`)
* **CI/CD & Sync:** `master-sync`, `update-docs`, `publish-showcase`, `deploy-hf-production`, `secure-checkpoint`
* **Data Engineering:** `daily-ingestion`, `build-etl`, `error-recovery`
* **Bootstrapping:** `bootstrap`, `git-discovery-preflight`, `generate-readme`

## 📂 Directory Structure
```text
.
├── .agents/            # The Control Plane: Rules, Skills, and Workflows (Human Edited)
├── .antigravity/       # The Data Plane: System metrics, graphs, and cache (System Managed)
├── .config/            # Environment configurations and MCP integrations
├── src/                # Application source code (FastAPI, Routers)
├── data/               # DuckDB metrics, Quarantine DLQs, and Parquet files
└── hf-webui/           # Hugging Face Spaces frontend deployment configurations
```
