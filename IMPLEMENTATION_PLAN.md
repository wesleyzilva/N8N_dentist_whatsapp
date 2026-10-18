# Fases de implementação — agentic TPM

Ordem fixa. Não pular fase: a seguinte depende da evidência da anterior.
Mapa: `docs/canonical/CANONICAL_MAP.md`. Gates: `docs/governance/PHASE_GATES.md`.

## Fase 0 — Governança (feita)

- Mapa canônico, RACI, RAID, rules/skills Cursor, contratos MCP
- Clínica 46/16 em `config/clinic.json`
- Guardrails de grounding
- Critério: TPM consegue abrir um card de sprint apontando P1–P10 sem inventar escopo

## Fase 1 — Canal e voz (P1, P10) (em andamento — domínio/HTTP prontos; import n8n pendente)

- Webhook WhatsApp estável no n8n
- Classificador + templates humanizados
- Estado mínimo da conversa
- Critério: mensagem de confirmação/dúvida recebe resposta no tom da secretária, sem fatos inventados

## Fase 2 — Unidade e presença (P3, P4)

- Resolver DDD 46 / 16 e cidade no texto
- Presença da dra só via evidência de calendário/bloco
- Critério: “a dra está em Pato Branco?” nunca é respondido sem tool; DDD 16 não força São Carlos se o texto disser Pato Branco

## Fase 3 — Agenda grounded (P2, P5)

- MCP Google Calendar: freebusy por unidade
- SecretaryVoice só cita slots retornados
- Critério: se o calendário falhar, a resposta pede espera ou escala; zero horários sintéticos

## Fase 4 — Mutação de agenda (P6)

- Confirmar, reagendar, cancelar com confirmação explícita do paciente
- Dual-write: evento Google + status no n8n
- Critério: nenhuma mutação sem intent CONFIRM explícito no turno

## Fase 5 — Triagem e humana (P7, P8)

- Regras de escalonamento (dor, emergência, menor, reclamação, baixa confiança)
- Handoff com resumo factual
- Critério: caso clínico não recebe conselho automatizado

## Fase 6 — Compliance e produção (P9)

- Opt-out, auditoria, horários de operação, observabilidade
- Critério: QA reproduz o fluxo com evidência; Security assina o gate

## Como o TPM usa isto

1. Escolher um ID P*
2. Abrir sprint card (`SPRINT_CARD_TEMPLATE.md`) com fase e gate
3. Atribuir `dev-agentic` + `qa-agentic` (e voz/security se P1/P9)
4. Dev só implementa contra MCP/schema existente
5. QA valida grounding (não só “o workflow rodou”)
6. Atualizar RAID ao fechar a fase
