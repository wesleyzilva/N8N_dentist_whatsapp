# Próximos passos

Fonte viva: `docs/governance/status.json` (`execution_steps` E0–E8 e backlog A1–A9) e o Painel do TPM Console (`npm run console`).

## Feito
- E0–E2: ambiente, código e testes verdes (pytest, 15 cenários, Console), serviço `POST /turn` e simulador.
- Estrutura limpa e canônica (`docs/governance/layout.json`); material antigo removido do repo.
- Grounding corrigido: calendário padrão vazio; ferramenta com erro degrada para pergunta ou espera.

## Agora: E3 Docker (stack local)
1. A8: promover `infra/docker/compose.target.yml` a `docker-compose.yml` e acrescentar a Evolution API.
2. A3: gerar `EVOLUTION_API_KEY`, `POSTGRES_PASSWORD` e `N8N_ENCRYPTION_KEY` novos no `.env`.
3. Construir a imagem do serviço Python e subir: `docker compose up -d --build`.
4. Painel > Integrações: n8n e Evolution verdes.

## Em seguida
- E4 banco (A9, migração 001, credencial no n8n) → E5 workflow no n8n e cenários contra ele → E6 WhatsApp real.
- E7 Fase 2: calendário por unidade (A4). E8 Fase 3: `GoogleCalendarGateway` real (A5).

Comandos: `pytest` · `npm run validate` · `npm run console` · `npm run test:console`
