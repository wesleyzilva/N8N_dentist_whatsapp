# Estrutura de pastas recomendada

## Objetivo

Organizar o projeto por domínio de negócio, infraestrutura e interfaces para manter o fluxo low-code simples, escalável e fácil de manter.

## Estrutura

```text
AGENTS.md
ARCHITECTURE.md
IMPLEMENTATION_PLAN.md
.cursor/rules/          # governança Cursor
.cursor/skills/         # tpm, architect, dev, qa, voice, security, devops
app/domains/            # intent, location, grounding
app/infrastructure/     # config + contratos MCP
app/interfaces/http/
config/clinic.json      # DDD 46 / 16
config/guardrails.json
docs/canonical/
docs/governance/
mcp/schemas/
tests/
workflows/
```

## Como usar

- Coloque regras de negócio em app/domains.
- Coloque integrações e acesso a dados em app/infrastructure.
- Coloque entradas/saídas externos em app/interfaces.
- Use workflows no n8n como orquestração, não como repositório de regras.
- Mantenha arquivos de configuração e JSON em config/.
