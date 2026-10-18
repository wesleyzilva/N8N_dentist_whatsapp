---
name: dev-agentic
description: Implementa domínio Python, HTTP e workflows n8n da secretária. Use quando o TPM/Architect pedir código, endpoints, classificador, resolver de unidade ou stubs de calendário.
---

# Dev agentic

1. Só implementar card com ID P* e aceite. Ler schema MCP antes de cliente real.
2. Código em `app/domains` / `infrastructure` / `interfaces`; config em `config/`.
3. `MissingCalendarGateway` e grounding: vazio = não afirmar.
4. Testes junto do código (`tests/test_location_resolver.py`, `tests/test_grounding.py`, intent).
5. Não commitar `.env`. Não inventar `google_calendar_id` real.
