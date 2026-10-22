# Workflows n8n

Orquestração do canal. Regras de unidade, agenda e tom ficam no Python (`POST /turn`).

## Fluxos
- `intent_workflow.json`: webhook `intent-webhook` → `http://host.docker.internal:8001/turn` → `reply_text` grounded.

Payload esperado no webhook:

```json
{ "message": "Vou confirmar minha consulta", "from": "5546999887766" }
```

Se `can_assert_facts` for false, o nó `Grounded Reply` marca `next` como `ask` ou `handoff`. Não colocar horário no canvas.

## Como importar
1. Abra o n8n.
2. Vá para Workflows > Import from JSON.
3. Selecione `intent_workflow.json`.
4. Suba `python -m app.interfaces.http.intent_service` (porta 8001) ou o container `intent-service` antes de ativar.
