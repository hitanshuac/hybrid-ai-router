# Knowledge Graph

- workspace: D:\Projects\Hybrid-AI-Router
- created_at_utc: 2026-05-17T16:20:05.642631+00:00
- nodes: 144
- edges: 195

## Summary
```json
{
  "file_count": 47,
  "walked_file_count": 47,
  "languages": {
    "Python": 16,
    "Markdown": 3,
    "YAML": 1,
    "JSON": 1
  },
  "frameworks": [
    "Python (requirements.txt)",
    "Docker",
    "Docker Compose"
  ],
  "type_distribution": {
    "other": 10,
    "code": 21,
    "documentation": 11,
    "data": 1,
    "media": 4
  },
  "semantic_files": 16,
  "semantic_edges": 137,
  "semantic_files_by_language": {
    "Python": 16
  },
  "semantic_edges_by_type": {
    "declares_package": 16,
    "defines": 46,
    "entrypoint": 1,
    "imports": 73,
    "tests": 1
  },
  "semantic_adapters": {
    "python": 16
  },
  "generic_fallback_file_count": 0,
  "parse_error_file_count": 0
}
```

## Sample Nodes
- workspace: Hybrid-AI-Router
- language: Python
- language: Markdown
- language: YAML
- language: JSON
- framework: Python (requirements.txt)
- framework: Docker
- framework: Docker Compose
- directory: data
- directory: docs
- directory: secrets
- directory: src
- other: .env.example
- other: .gitignore
- other: .webui_secret_key
- code: docker-compose.yml
- other: Dockerfile
- code: HANDOVER.md
- other: Hybrid-AI-Router.code-workspace
- other: LICENSE

## Sample Edges
- workspace:D:\Projects\Hybrid-AI-Router --uses_language--> language:python
- workspace:D:\Projects\Hybrid-AI-Router --uses_language--> language:markdown
- workspace:D:\Projects\Hybrid-AI-Router --uses_language--> language:yaml
- workspace:D:\Projects\Hybrid-AI-Router --uses_language--> language:json
- workspace:D:\Projects\Hybrid-AI-Router --uses_framework--> framework:python_(requirements.txt)
- workspace:D:\Projects\Hybrid-AI-Router --uses_framework--> framework:docker
- workspace:D:\Projects\Hybrid-AI-Router --uses_framework--> framework:docker_compose
- workspace:D:\Projects\Hybrid-AI-Router --contains--> dir:data
- workspace:D:\Projects\Hybrid-AI-Router --contains--> dir:docs
- workspace:D:\Projects\Hybrid-AI-Router --contains--> dir:secrets
- workspace:D:\Projects\Hybrid-AI-Router --contains--> dir:src
- workspace:D:\Projects\Hybrid-AI-Router --contains--> file:.env.example
- workspace:D:\Projects\Hybrid-AI-Router --contains--> file:.gitignore
- workspace:D:\Projects\Hybrid-AI-Router --contains--> file:.webui_secret_key
- workspace:D:\Projects\Hybrid-AI-Router --contains--> file:docker-compose.yml
- workspace:D:\Projects\Hybrid-AI-Router --contains--> file:Dockerfile
- workspace:D:\Projects\Hybrid-AI-Router --contains--> file:HANDOVER.md
- workspace:D:\Projects\Hybrid-AI-Router --contains--> file:Hybrid-AI-Router.code-workspace
- workspace:D:\Projects\Hybrid-AI-Router --contains--> file:LICENSE
- workspace:D:\Projects\Hybrid-AI-Router --contains--> file:README.md
