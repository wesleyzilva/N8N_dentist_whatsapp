# MCPs — contratos para TPM, Dev e QA

Estes JSON Schema são a interface. Cursor (dev-agentic / qa-agentic) e o n8n só falam com o mundo externo por aqui. Implementar o servidor MCP na Fase 3 sem mudar o schema.

Catálogo: `mcp/catalog.json`. Exemplo de config Cursor: `mcp/cursor-mcp.example.json`.

| MCP | Problema | Operações |
|---|---|---|
| `clinic-locations` | P3 | `list_units`, `resolve_unit` |
| `google-calendar` | P4, P5, P6 | `freebusy`, `presence`, `create_event` (Fase 4) |
| `whatsapp` | P1, P8 | `send_text`, `handoff` |
| `guardrails` | P2, P7 | `allowed_claims`, `tone_policy` |
| `n8n-ops` | P10 | `import_workflow`, `run_webhook` (DevOps) |

Regra: se o MCP retornar vazio/erro, o runtime trata como evidência ausente — não como “modelo completa”.
