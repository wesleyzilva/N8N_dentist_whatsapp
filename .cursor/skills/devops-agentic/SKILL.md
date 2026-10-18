---
name: devops-agentic
description: Docker Compose, n8n, env e operação local. Use para subir stack, webhook, timezone America/Sao_Paulo e preparar OAuth Google na Fase 3.
---

# DevOps agentic

- Stack: `docker-compose.yml` (n8n + postgres) + `python intent_service.py`.
- TZ `America/Sao_Paulo`. Calendários 46 e 16 são IDs distintos no env.
- Não habilitar MCP Google no Cursor até OAuth real (`mcp/cursor-mcp.example.json`).
- Documentar comando de validação em `scripts/` quando mudar o fluxo local.
