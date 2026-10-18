# Sprint — Canal e voz grounded

## Título
- [x] Webhook → `/turn` → texto da secretária sem fatos inventados

## Descrição
- Fase 1. IDs: P1 (voz), P2 (não alucinar), P10 (orquestração n8n).
- Objetivo: mensagem de confirmação/dúvida/horário recebe resposta humanizada só com `allowed_claims`.
- Calendário ainda é `MissingCalendarGateway` (Fase 3).

## Critérios de aceite
- [x] POST `/turn` devolve o contrato canônico (intent, unit_hypothesis, evidências, claims, escalation, reply_text)
- [x] Tom vem de `config/voice.json`
- [x] Sem slot de agenda quando a ferramenta está vazia
- [x] Sem cidade da dra quando presença está `missing`
- [x] Pedido clínico escala

## Dependências
- [x] Classificador e grounding da Fase 0
- [ ] Provedor WhatsApp real (stub local)
- [ ] Google Calendar (Fase 3)

## Responsável
- Dev: domínio + HTTP + workflow
- QA: pytest do round-trip e alucinação
- Voice: templates
- TPM: fase 1

## Status
- [x] Em andamento (gate local via pytest; n8n import manual)
