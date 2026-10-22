# Documentação

Ordem de leitura para quem chega: `AGENTS.md` (raiz) → `canonical/CANONICAL_MAP.md` → `governance/status.json` (ou o Painel do TPM Console).

| Pasta / arquivo | O que é |
|---|---|
| `canonical/CANONICAL_MAP.md` | Fonte única do produto: problemas P1–P10, unidades, contrato de resposta |
| `governance/status.json` | Registro do TPM: passo a passo (E0–E8), fases, problemas, backlog A*, inventário |
| `governance/layout.json` | Contrato da estrutura do repositório (testado no pytest e no Console) |
| `governance/NEXT_STEPS.md` | O que fazer agora, em texto |
| `governance/PHASE_GATES.md` | Critério de saída de cada fase |
| `governance/RAID.md`, `RACI.md` | Riscos e responsabilidades |
| `governance/VALIDATION_LOG.md` | Evidências de validação (append-only) |
| `governance/PERSONA_AGENTS.md` | Stakeholders simulados (opinam, não implementam) |
| `sprints/` | Cards de sprint; `_TEMPLATE.md` é o molde |

Na raiz ficam só `README.md`, `AGENTS.md`, `ARCHITECTURE.md` e `IMPLEMENTATION_PLAN.md`.

Material removido (VIPpocket, plano mestre antigo, código `legacy/`, agente Gemini no n8n, schema `clinica`) continua no histórico do git: `git show a0048aa:<caminho>`.
