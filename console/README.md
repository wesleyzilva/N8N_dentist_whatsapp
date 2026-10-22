# TPM Console

Frontend local para o TPM acompanhar o projeto, validar o que dá para validar e simular conversas.
Node 20+ sem dependências (nada de `npm install`). Python 3.10+ para testes e para o serviço `/turn`.

```bash
npm run console        # http://localhost:4173 (inicia o serviço Python na 8001 com simulação ligada)
npm run validate       # mesma validação no terminal; exit 1 se falhar algo de código (integrações não derrubam; use --strict)
npm run test:console   # testes do próprio Console
```

Windows (PowerShell): os mesmos comandos funcionam. Se o Python não for achado, `$env:PYTHON="C:\caminho\python.exe"`.
Primeira vez: `pip install -r requirements-dev.txt`.

## Abas

| Aba | Para que serve |
|---|---|
| Painel do TPM | Passo a passo da execução (E0–E8), fases 0–6 com gate, P1–P10 (declarado × código verificado × ambiente), pontos de atenção, backlog, RAID, inventário do que já temos, histórico de validações |
| Simulador de conversa | Chat estilo WhatsApp. Escolha o número (DDD 46/16/outro), o calendário (vazio, erro, fixture) e o alvo (Python direto ou webhook n8n). Clique numa resposta para ver o contrato: intent, unidade, evidências, claims, escalonamento, tool_status. O lint avisa se houver horário ou cidade da dra sem evidência. "Copiar como cenário" gera JSON para a suíte |
| Cenários de teste | Suíte de conversas (`tests/scenarios/conversations.json`): em processo, contra o serviço HTTP ou contra o n8n. "Reproduzir no simulador" repete o diálogo |
| Validações | pytest, cenários, configuração, MCP, workflows n8n (auditoria estática), Docker Compose, segredos, `.env`, higiene, governança, integrações |
| Integrações | Probes reais: serviço Python, n8n, webhook, Evolution API, PostgreSQL, Docker, Google Calendar, Gemini |
| Documentos | Mapa canônico, plano, governança e READMEs |

## Onde o TPM edita

- `docs/governance/status.json`: passos de execução (`execution_steps`, passo atual em `current_step`), fases, status declarado, passos manuais, backlog (A*), inventário. O Console cruza com a evidência; divergências aparecem em vermelho.
- `docs/governance/RAID.md`: tabela lida pelo Painel.
- `tests/scenarios/conversations.json`: novos casos de conversa (rodam no pytest e no Console).

## Modos de calendário do simulador

| Modo | O que simula | Esperado da secretária |
|---|---|---|
| Sem ferramenta | Estado real do MVP | Pergunta/espera; nunca horário nem cidade da dra |
| Ferramenta com erro | Timeout/OAuth expirado | Mesmo comportamento; `tool_status.freebusy = error` |
| Fixture | Resultado fixo de teste (Fase 3) | Cita só os slots devolvidos e a cidade do evento de presença |

`/simulate/turn` só existe quando o serviço sobe com `SIMULATION_ENABLED=1` (o Console faz isso). O `/turn` de produção ignora `calendar_mode`.

## Variáveis

| Variável | Padrão |
|---|---|
| `CONSOLE_PORT` | 4173 |
| `SERVICE_PORT` / `SERVICE_URL` | 8001 / `http://127.0.0.1:8001` |
| `N8N_URL` / `N8N_WEBHOOK_PATH` | `http://localhost:5678` / `/webhook/intent-webhook` |
| `EVOLUTION_URL` | `EVOLUTION_API_URL` do `.env` ou `http://localhost:8080` |
| `PYTHON` | detecta `python3`, `python`, `py` |

## Segurança

- Só escuta em 127.0.0.1, recusa `Host` que não seja local e exige o cabeçalho `X-TPM-Console` nos POST.
- Lê `.env` apenas para dizer se uma variável está definida; valores nunca são enviados ao navegador.
- O único acesso externo é o botão opcional do Gemini (lista modelos, sem gastar tokens).
- Leitura de documentos restrita a uma lista de `.md` do repositório.

## Estrutura

```text
console/server.mjs        servidor HTTP + CLI (--check, --json, --strict, --no-service)
console/lib/checks.mjs    checagens (pytest, cenários, config, workflows, segredos, ...)
console/lib/integrations.mjs  probes
console/lib/status.mjs    cruza status.json com evidência, RAID, histórico (console/.cache, ignorado no git)
console/lib/service.mjs   gerencia o processo Python
console/public/          SPA em JavaScript puro
console/test/            node:test
```
