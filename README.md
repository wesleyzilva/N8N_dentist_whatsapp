# Secretária WhatsApp — Harmonização orofacial

<p align="center">
  <img src="https://img.shields.io/badge/n8n-Workflow%20Automation-00A4F4?style=for-the-badge&logo=n8n&logoColor=white" />
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white" />
  <img src="https://img.shields.io/badge/WhatsApp-Integration-25D366?style=for-the-badge&logo=whatsapp&logoColor=white" />
</p>

Secretária digital no WhatsApp do consultório de **harmonização orofacial** (não é consultório odontológico geral): atendimento humanizado, duas unidades (Pato Branco DDD 46 e São Carlos DDD 16), agenda no Google Calendar (Fase 3) e guardrails para não alucinar horário, procedimento, preço nem a cidade da dra.

Governança agentic (TPM, Dev, QA, MCPs): `AGENTS.md` e `docs/canonical/CANONICAL_MAP.md`.

## Acompanhamento do TPM (comece por aqui)

```bash
npm run console      # http://localhost:4173  (Node 20+, sem dependências; inicia o serviço Python sozinho)
npm run validate     # mesma validação no terminal (exit 1 se algo de código falhar)
```

O **TPM Console** mostra fases e P1–P10 com evidência automática, roda testes, valida configuração, workflows,
segredos e integrações, e traz um **simulador de conversa** (calendário vazio, com erro ou fixture) e a suíte de
cenários anti-alucinação. Detalhes em [`console/README.md`](console/README.md).

## Overview

- receber o paciente no Zap com tom de secretária
- classificar intenção (confirmar, reagendar, cancelar, dúvida, horário, cidade)
- tratar DDD 46/16 como hipótese de unidade na região que ela atende, não como “onde a dra está”
- só citar disponibilidade/presença com evidência de calendário
- escalar para humana quando faltar fato ou houver risco clínico

## What This Project Includes

- webhook-driven inbound message handling
- intent classification with configurable guardrails
- local-first development with Docker Compose
- n8n-based orchestration for low-code workflows
- testable domain logic and validation scripts
- a clear separation between domain, infrastructure, and interface layers

## Architecture at a Glance

The solution is organized into three main layers:

- Domain layer: business logic for intent classification and workflow rules
- Infrastructure layer: configuration loading, persistence, and environment handling
- Interface layer: HTTP endpoints and workflow integration points

### Main Components

- n8n: orchestration and workflow execution
- Python service: intent classification endpoint
- PostgreSQL: local persistence for n8n data
- Docker Compose: local environment startup
- Usar: Google Calendar, WhatsApp providers, and LLM services

## Repository Structure

```
app/         domínio (domains), infraestrutura (infrastructure) e entradas (interfaces: http, n8n)
config/      clinic, guardrails, voz, sessão (fatos e regras, nunca no prompt)
mcp/         contratos MCP
workflows/   fluxos n8n (só orquestram)
tests/       pytest + tests/scenarios/conversations.json (suíte de conversas)
scripts/     runner de cenários
console/     TPM Console (Node, sem dependências)
infra/       Docker (infra/docker), banco (infra/db) e migração local → nuvem
docs/        canonical/ (mapa), governance/ (status.json, RAID, gates, layout.json), sprints/
```

Índice completo e contrato da estrutura: [`docs/README.md`](docs/README.md) e `docs/governance/layout.json`.

## Prerequisites

- Docker Desktop and Docker Compose
- Python 3.10+
- Git
- optional: Google Cloud project and WhatsApp provider credentials for full production integration

## Quick Start

1. Clone the repository
   ```bash
   git clone https://github.com/wesleyzilva/N8N_dentist_whatsapp.git
   cd N8N_dentist_whatsapp
   ```

2. Create the local environment file
   ```bash
   copy .env.example .env
   ```

3. Start the local stack
   ```bash
   docker compose up -d
   ```

4. Start the turn service (intent + grounding + voice). O TPM Console já faz isso; manualmente:
   ```bash
   python -m app.interfaces.http.intent_service
   ```

   Local contract: `POST http://localhost:8001/turn` with `{"message": "...", "whatsapp_number": "5546..."}`.

5. Validate locally
   ```bash
   pip install -r requirements-dev.txt
   pytest
   npm run validate
   ```

   Conversas contra o serviço ou o n8n: `python -m scripts.run_scenarios --url <endpoint>` (ver `scripts/README.md`).

## Configuration

The project expects environment variables such as:

- N8N_BASIC_AUTH_USER / N8N_BASIC_AUTH_PASSWORD
- WEBHOOK_URL
- GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET
- OPENAI_API_KEY or another LLM provider key
- WHATSAPP_API_URL / WHATSAPP_API_TOKEN

See [.env.example](.env.example) for the reference template.

## Testing

The repository includes automated tests for:

- intent classification behavior
- guardrail configuration loading
- grounded secretary voice (no invented slots)
- HTTP round-trip on `/turn`
- project structure expectations

Run them with:

```bash
pytest
```

## Safety and Governance

When a decision could create clinical, legal, or financial risk, AI should not make the final decision on its own. It should gather the relevant information, structure the context clearly, and route the case to the responsible human or operational process.

## Roadmap

Ver fases em `IMPLEMENTATION_PLAN.md`. Próximo: Fase 1 (canal + voz) e Fase 2 (unidade/presença).

## License

This project is intended for internal and experimental use. Review credentials and secrets before production deployment.
