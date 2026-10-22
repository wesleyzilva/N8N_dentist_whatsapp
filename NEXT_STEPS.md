# Próximos passos

Fonte detalhada e viva: `docs/governance/status.json` (backlog A1–A8) e o Painel do TPM Console (`npm run console`).

## Feito
- Fase 0: mapa canônico P1–P10, RACI, RAID, rules/skills Cursor, contratos MCP.
- Fase 1 (código): `POST /turn` com intent, unidade (hipótese), grounding e `reply_text`; voz por templates; sessão curta.
- TPM Console: painel por fase/P*, validações, integrações, simulador de conversa e 15 cenários anti-alucinação.
- Correção do grounding: calendário padrão vazio; ferramenta com erro degrada para pergunta/espera.

## Agora (fechar o gate da Fase 1)
1. `docker compose up -d` (defina `EVOLUTION_API_KEY` no `.env`) e abra o Console > Integrações.
2. Importar e ativar `workflows/intent_workflow.json` no n8n; conferir "Webhook intent-webhook" verde.
3. Console > Cenários > "Contra o n8n" e anotar a evidência no `VALIDATION_LOG.md`.
4. Decidir A2 (tirar regra de negócio do canvas) antes de ativar qualquer nó de reserva.

## Em seguida
- Fase 2: calendário distinto por unidade e validação da premissa da dona (A4).
- Fase 3: `GoogleCalendarGateway` real atrás do protocolo (A5).

Comandos: `pytest` · `npm run validate` · `npm run console` · `npm run test:console`
