# Infra

Tudo que sobe fora do Python: containers e banco. O n8n só orquestra; regras ficam em `app/` e `config/`.

```
docker-compose.yml          (raiz) stack atual: postgres + n8n + Evolution API
infra/
  docker/
    compose.target.yml      compose alvo: postgres (healthcheck) + intent-service + n8n, sem segredo fixo
    Dockerfile.intent       imagem do serviço Python (python -m app.interfaces.http.intent_service)
  db/
    migrations/             SQL do banco `secretaria` (conversation_state, processed_messages)
  LOCAL_TO_CLOUD.md         migração do compose atual para o alvo e checklist de nuvem
```

## Como seguir (passos E3 e E4 do Painel)

1. E3 — unificar os compose (A8): promover `compose.target.yml`, acrescentar a Evolution API, exigir `POSTGRES_PASSWORD`, `N8N_ENCRYPTION_KEY` e `EVOLUTION_API_KEY` no `.env`.
2. E3 — construir a imagem do serviço e conferir `healthz`.
3. E4 — aplicar `infra/db/migrations/001_secretaria_fase1.sql` e criar a credencial Postgres no n8n.

## Decisões já tomadas

- Agenda e presença da dra vêm do Google Calendar, não do banco. Por isso o schema `clinica` (pacientes, agendamentos, procedimentos) foi removido; o banco guarda só estado mínimo de conversa e deduplicação de webhook (A9 confirma).
- Nunca `docker compose down -v` (apaga os volumes `n8n-db` e `n8n-data`).
- Portas só em `127.0.0.1`; dados de pacientes são dados de saúde (LGPD).
