# VALIDATION_LOG — Secretária WhatsApp (harmonização orofacial)

Log vivo da validação passo a passo. Segue `VALIDATION_FLOW.md` e `delivery_checklist.json`.
Fase em validação: **Fase 1 — Canal e voz (P1, P10)**. Gate: ver `IMPLEMENTATION_PLAN.md` e `NEXT_STEPS.md`.
Última atualização: 2026-10-17 (rodada 4).

**Convenções**
- Quem executa: `[Claude]` análise estática sobre arquivos enviados no chat; `[Wesley]` execução local (Docker, Python, n8n).
- Status: ✅ passou · ❌ falhou · ⚠️ passou com ressalva · ⏳ pendente · ⛔ bloqueado
- Nunca registrar valores de segredo neste arquivo. Só nome da variável e se está preenchida.

---

## 1. Plano de validação (gate da Fase 1)

| ID | Passo | Quem | Comando / ação | Resultado esperado | Status |
|---|---|---|---|---|---|
| V0 | Validação estática dos artefatos | Claude | JSON/YAML, diff de variáveis, arquivos referenciados | Sintaxe válida, inconsistências mapeadas | ✅ (L-001..L-005, L-016) |
| V1 | Pré-requisitos da máquina | Wesley | versões + `docker info` | Daemon ativo | ✅ (L-007) |
| V2 | Decidir compose alvo, ajustar `.env` e aplicar | Wesley | Seção 3 (Passo 2) | `config --services` lista `postgres`, `intent-service`, `n8n` | ⚠️ `.env` pronto (L-025); faltam o **backup** (dump ausente) e copiar os 3 arquivos do B |
| V3 | Stack no ar | Wesley | `docker compose up -d --build` · `ps` · `logs` | Todos `running`/`healthy`; UI em http://localhost:5678 | ⚠️ no ar com o compose **antigo** (L-011); repetir após aplicar B |
| V4 | Testes automatizados | Wesley | `python -m pytest -q` e exit code | Exit code 0, todos verdes | ✅ 33 passed, exit 0 (L-027) |
| V5 | Serviço `/turn` isolado | Wesley | POST em `http://localhost:8001/turn` (seção 4) | JSON com `intent`, unidade e `reply_text`; sem horário inventado | ⛔ conexão recusada (L-015) |
| V6 | Workflow importado e coerente | Wesley | Query da seção 3 (passo 1) | Um workflow ativo; nó HTTP aponta para o serviço certo | ⚠️ ativo usa `/turn` via `host.docker.internal` (L-020); ajustar após B |
| V7 | POST no webhook do n8n | Wesley | POST em `/webhook/intent-webhook` com payload `{"message":"...","from":"5546..."}` (o webhook usa `from`; o `/turn` usa `whatsapp_number`) | Resposta ao paciente = `reply_text` | ⏳ |
| V8 | QA de alucinação | Wesley + Claude | Casos A–D da seção 4 | Nenhum horário/cidade da dra sem evidência | ⏳ |
| V9 | Fechar o gate | Ambos | Atualizar `delivery_checklist.json`, `NEXT_STEPS.md`, RAID | Evidências anexadas | ⏳ |

---

## 2. Achados

| ID | Sev. | Achado | Ação sugerida | Status |
|---|---|---|---|---|
| F-01 | Alto | `.env` é cópia do template: senha n8n `changeme`, Google, OpenAI e WhatsApp com valores de placeholder. | OK para Fase 1 (nada disso é consumido). Bloqueia Fase 3. Trocar antes de expor por túnel público. | ⚠️ aceito p/ Fase 1 |
| F-02 | Alto | **Correção (rodada 2):** a `N8N_ENCRYPTION_KEY` do `.env` foi extraída do container em uso (L-008), logo é a chave **real** do n8n atual. A recomendação anterior de "gerar chave nova" estava errada: trocar a chave sem re-criptografar quebra as credenciais salvas. O compose **atual** não repassa a chave ao container; o cloud-ready (B) repassa e exige. | Manter a chave extraída. Backup dela fora do repo (gerenciador de senhas). Rotacionar só com plano de re-criptografia. Risco de ter aparecido no chat é baixo enquanto o Postgres não está exposto, mas registre. | ⚠️ resolvido ao adotar B |
| F-03 | Médio | `N8N_BASIC_AUTH_*` no compose atual: basic auth foi removido do n8n na 1.0; provavelmente sem efeito na 2.x. B já remove essas variáveis. | Confirmar no primeiro acesso à UI (V3) e remover do `.env.example`. | ⏳ |
| F-04 | Médio | Compose atual usa `n8nio/n8n:latest`. B usa `${N8N_VERSION:-latest}`; `.env` tem `N8N_VERSION=2.30.4`. | **Confirmado (L-017):** o n8n em execução é 2.30.4, igual ao `.env`. Fixar é seguro. Pré-puxar a tag com `docker pull n8nio/n8n:2.30.4` (falha sem tocar nos containers se a tag não existir). | ✅ |
| F-05 | Médio | `WEBHOOK_URL` do `.env` era placeholder com `/webhook` no fim. **Corrigido (L-025):** `.env:7` agora é `WEBHOOK_URL=http://localhost:5678/`. Para túnel/nuvem, usar a URL pública terminando em `/`. | — | ✅ |
| F-06 | Baixo | Duas fontes de verdade para o Postgres (compose antigo com `n8n/n8n` fixo; `.env` com `POSTGRES_*` e `DB_POSTGRESDB_*`). B lê do `.env`; `DB_POSTGRESDB_USER/PASSWORD/DATABASE` do `.env` passam a ser ignoradas. | Manter só `POSTGRES_*` no `.env`. | ⏳ |
| F-07 | Baixo | `.env` sem `PORT`, `GOOGLE_CALENDAR_*`. B fixa `PORT: 8001` no serviço. | `GOOGLE_CALENDAR_*` só na Fase 3. | ⏳ |
| F-08 | Info | B **remove** `extra_hosts: host.docker.internal`. **Os dois** JSONs (`intent_workflow.json` e `intent_workflow_simple.json`) chamam `http://host.docker.internal:8001/turn` (L-024). No Docker Desktop esse nome ainda resolve; numa VM Linux, não. | Em V6, trocar para `http://intent-service:8001/turn` nos dois JSONs e reimportar. Não usar `$env` no nó (n8n 2.x bloqueia por padrão). | ⏳ |
| F-09 | Info | `delivery_checklist.json` ainda é o template (`"exemplo"`). | Preencher em V9. | ⏳ |
| F-10 | Info | `SETUP_COMMANDS.md` usa `cd /d` em bloco PowerShell (sintaxe de cmd). | `Set-Location E:\wesleyzilva\repo\N8N_dentist_whatsapp`. | ⏳ |
| F-11 | Info | Os arquivos citados na documentação **existem** localmente (`git status`: `config/clinic.json`, `voice.json`, `docs/canonical/`, `mcp/`, `tests/test_*`, `scripts/import_n8n_workflow.ps1`...), mas ainda não foram enviados ao chat. `db/` e `docs/` chegaram vazios (0 bytes). | Para V6–V8 estático: enviar `workflows/intent_workflow.json`, `app/interfaces/http/intent_service.py` e `docs/canonical/CANONICAL_MAP.md`. | ⚠️ |
| F-12 | Alto | **Dois composes incompatíveis disputam `docker-compose.yml`.** A: `postgres:16-alpine`, `name: dentist_whatsapp`, volumes `postgres_data`/`n8n_data`, porta 5432 no host, sem `intent-service`, sem `./workflows`. B (cloud-ready): `postgres:15`, sem `name:`, volumes `n8n-db`/`n8n-data`, com `intent-service`. Aplicar A criaria projeto e volumes novos e vazios (workflows e credenciais atuais ficariam órfãos) e o pg16 não abre dados do pg15. | Adotar **B** como `docker-compose.yml`. Não aplicar A. | ⏳ aguardando confirmação |
| F-13 | Alto | O `docker-compose.yml` do repo **não foi substituído**. **Reconfirmado (L-025):** `config --services` lista 2 serviços; `docker-compose.yml:3` é `postgres:15`; não há `intent-service`. `Dockerfile.intent` e `.dockerignore` seguem ausentes (L-018; a checagem de L-025 saiu truncada). | Backup, baixar os 3 arquivos do chat e copiar (Passo 2). | ❌ aberto |
| F-14 | Médio | **Revisado de novo (L-024):** `XNTM…` é uma **versão antiga do mesmo workflow** (chamava `/classify`), importada antes de o JSON ter `id`. O `intent_workflow.json` atual tem `id: j9ZLd2huqjyrghXf`, então reimportar sobrescreve o ativo (idempotente). `import_n8n_workflow.ps1` já desativa `XNTM…` por id fixo. `intent_workflow_simple.json` **não** está no n8n (nome diferente, sem `id`). `/classify` ainda é servido pelo `intent_service.py` (L-026), então `XNTM…` está obsoleto, não quebrado. | Excluir `XNTM…` na UI. Ver F-25 e F-27. | ⏳ |
| F-15 | Médio | **Verificado (L-019):** `intent_service.py` responde em `/healthz` e `/` e `run_server` escuta em `0.0.0.0` com `PORT` do ambiente (padrão 8001). O healthcheck e a publicação de porta do B são compatíveis. | — | ✅ |
| F-16 | Médio | **Fechado (L-022):** `docker pull n8nio/n8n:2.30.4` devolveu digest `sha256:d1606a508b1e…`, o mesmo prefixo do ID da imagem `latest` em uso. É a mesma imagem. | — | ✅ |
| F-17 | Baixo | `.pyc` estão **versionados** (≈20 em `git status`). O `.gitignore` proposto (`.env`, `*.zip`) não cobre `__pycache__`, `.pytest_cache`, `.venv` e, sozinho, não desrastreia o que já está no git. `.env` não aparece no status (ok). | Mesclar com o `.gitignore` atual (não sobrescrever) e depois `git ls-files "*.pyc" \| ForEach-Object { git rm --cached -q $_ }`. | ⏳ |
| F-18 | Baixo | `.env.example` novo traz `POSTGRES_USER=clinica_admin` (o usuário real do volume é `n8n`) e remove `PORT`, `TZ`, `N8N_VERSION`, `BIND_ADDR`, `N8N_PROTOCOL`, `N8N_PROXY_HOPS`, `GOOGLE_*`, `OPENAI_*`, `WHATSAPP_*`, `GOOGLE_CALENDAR_*`. | Mesclar, não substituir. Usar `POSTGRES_USER=n8n` no exemplo. | ⏳ |
| F-19 | Info | A regex `'^\s*[A-Za-z_]+='` ignora variáveis com dígito (`N8N_HOST`, `N8N_VERSION`, `N8N_ENCRYPTION_KEY`...). A listagem de nomes do L-008b ficou incompleta. | Usar `[A-Za-z0-9_]+`. | ✅ corrigido na seção 3 |
| F-20 | Decisão | O README novo descreve um banco `clinica` (pacientes, profissionais, procedimentos, agendamentos, lembretes) criado por `db/init/*.sql`. `db/init` **não existe** no repo (L-014) e esse banco não consta em `ARCHITECTURE.md` nem nas Fases 0–6. O README também fala em "clínica odontológica", e `AGENTS.md` diz que é harmonização orofacial e manda ler o `CANONICAL_MAP.md` antes de mudar. Dados de paciente = LGPD (Fase 6). | Decisão do TPM: entra no mapa canônico? Em qual P* e fase? Até lá, **fora do gate da Fase 1**. | ⏳ decisão |
| F-21 | Alto | `validate_local_flow.ps1` **não falha quando o pytest falha**: `$ErrorActionPreference = "Stop"` não captura o código de saída de executável nativo e não há checagem de `$LASTEXITCODE` após `python -m pytest -q`. O script imprime "Validação concluída" mesmo com testes quebrados. | Patch 1 (seção 5). Até corrigir, rodar `python -m pytest -q` à parte e registrar o exit code. | ❌ aberto |
| F-22 | Médio | O único teste anti-alucinação do script é um `-match` com dois literais (`14h` e `09:00`). Não pega `15h`, `10:30`, `9h` etc. e não confere `can_assert_facts`. `AGENTS.md` proíbe aprovar sem caso de alucinação. | Patch 2 (seção 5). | ⏳ |
| F-23 | Médio | O script posta `{message, from}` em `/turn`. **Verificado (L-026):** `intent_service.py` lê `payload.get("whatsapp_number") or payload.get("from")`, então `/turn` aceita os dois campos. | — | ✅ |
| F-24 | Médio | Se o serviço não responde, o script **inicia `python intent_service.py` oculto no host**, que ocupa a 8001 e colide com o `intent-service` do B. **Hoje não há processo órfão (L-026: nada escutando na 8001).** O risco permanece enquanto o auto-start existir. | Patch 3 (seção 5) ao adotar o B. | ⚠️ latente |
| F-25 | Médio | `import_n8n_workflow.ps1` não é portável: `--projectId=eqLFJhy2q3uyLDDO` e os ids `XNTM…`/`j9ZL…` fixos no código, mais `restart` do n8n a cada importação. Em instalação nova (VM/nuvem) o `projectId` não existe e o script quebra. | Omitir ou descobrir o `projectId` em vez de fixar; parametrizar os ids; mover a desativação de `XNTM…` para uma limpeza única. | ⏳ |
| F-26 | Médio | Webhook `intent-webhook` **sem autenticação**. Aceitável local; vira risco ao expor por túnel/URL pública (`WEBHOOK_URL`). | Antes de expor: token em header ou validação de assinatura do provedor (gate da Fase 6, Security). | ⏳ Fase 6 |
| F-27 | Baixo | `intent_workflow_simple.json` não tem `id`: cada importação cria **mais uma** cópia (mesma causa de `XNTM…`). | Fixar um `id` no JSON ou parar de importá-lo. | ⏳ |
| F-28 | Baixo | O espelho `scripts/n8n_grounded_reply.py` diverge do nó Code: sem `escalation`, o nó usa `{needed:false, reason:null}` e o espelho usa `{}`. Os testes cobrem o espelho, não o nó real. | Alinhar o default no espelho. | ⏳ |
| F-29 | Baixo | `validate_delivery.py` devolve `status: ready` para o template (`delivery_name: "exemplo"`): só checa se as listas existem. | Em V9, reprovar `exemplo` ou ausência de evidência. | ⏳ |
| F-30 | Info | **Não reproduzido (L-027):** os 33 testes passam, incluindo `test_guardrails_config` e o round-trip HTTP de `/turn`. O caminho padrão de `load_guardrails()` não causou erro. | Sem ação. Reabrir se aparecer `FileNotFoundError` dentro do container. | ✅ |

---

## 3. Próximos comandos (PowerShell)

**Passo 1 — leitura: concluído** (L-017..L-021). Gates de V2 cumpridos: versão do n8n, `/healthz` e bind do serviço.

**Passo 1b — concluído** (L-025..L-027). V4 passou (33 testes) e o `.env` está pronto. Faltam o backup e a aplicação do B.

**Passo 2 — aplicar o compose B (cloud-ready)**

Cole **um bloco por vez** (na rodada anterior a colagem juntou linhas). Baixe do chat para Downloads: `docker-compose.cloud-ready.yml`, `Dockerfile.intent` e `_dockerignore`.

```powershell
# A) Backup FORA do repo (o dump contém credenciais criptografadas)
Copy-Item docker-compose.yml $env:TEMP\docker-compose.before.yml
docker compose exec postgres pg_dump -U n8n -d n8n -Fc -f /tmp/n8n_before.dump
docker compose cp postgres:/tmp/n8n_before.dump $env:USERPROFILE\Documents\n8n_before.dump
Get-Item $env:USERPROFILE\Documents\n8n_before.dump | Select-Object Name, Length
```

```powershell
# B) Conferir os arquivos baixados
$d = "$env:USERPROFILE\Downloads"
Get-ChildItem "$d\docker-compose.cloud-ready.yml", "$d\Dockerfile.intent", "$d\_dockerignore" | Select-Object Name, Length
```

Tamanhos esperados: **3579**, **604** e **287** bytes. O compose pg16 (errado, F-12) tem 2147 bytes: se aparecer esse tamanho, é o arquivo errado.

```powershell
# C) Copiar para a raiz do repo
Copy-Item "$d\docker-compose.cloud-ready.yml" .\docker-compose.yml -Force
Copy-Item "$d\Dockerfile.intent" .\Dockerfile.intent
Copy-Item "$d\_dockerignore" .\.dockerignore
docker compose config --services
docker compose config | Select-String 'WEBHOOK_URL'
```

```powershell
# D) Subir (só se o compose for o B)
$n = (docker compose config --services | Measure-Object).Count
if ($n -eq 3) { docker compose up -d --build } else { "ERRO: $n serviços (esperado 3). Não subir." }
```

```powershell
# E) Verificar
docker compose ps
docker volume ls --format "{{.Name}}"
docker compose logs n8n --tail 20
Invoke-RestMethod http://localhost:8001/healthz
docker compose exec postgres psql -U n8n -d n8n -c "SELECT id, name, active FROM workflow_entity"
$body = @{ message = 'Oi, quero confirmar minha consulta'; whatsapp_number = '5546999999999' } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://localhost:8001/turn -ContentType 'application/json' -Body $body
```

Esperado: 3 serviços no passo C e `WEBHOOK_URL: http://localhost:5678/`; no passo E, `postgres` e `intent-service` `healthy`, `n8n` `running`; **nenhum volume novo** (os mesmos `…_n8n-db` e `…_n8n-data`); os mesmos 2 workflows; `/turn` devolve `reply_text`. Se o n8n acusar chave de criptografia divergente, ele recusa iniciar sem alterar dados: pare e envie `docker compose logs n8n --tail 30`. **Não cole a saída completa de `docker compose config`** (imprime senha e chave).

**Rollback** (volumes não são tocados): `docker compose down` (**nunca** `-v`), `Copy-Item $env:TEMP\docker-compose.before.yml .\docker-compose.yml -Force`, `docker compose up -d`.

---

## 4. Casos de teste para V5, V7 e V8

Substitua o texto entre aspas simples pelo caso. **Não envie `<TEXTO>` literal** (foi o que aconteceu em L-015).

```powershell
$body = @{ message = 'Oi, quero confirmar minha consulta'; whatsapp_number = '5546999999999' } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://localhost:8001/turn -ContentType 'application/json' -Body $body
```

| Caso | `message` | Esperado |
|---|---|---|
| Sanidade | `Oi, quero confirmar minha consulta` | `intent=CONFIRM`; tom da secretária; sem mutação de agenda (Fase 4) |
| A. Presença da dra | `A dra esta em Pato Branco hoje?` | Sem tool de calendário, não afirma. Pergunta/espera ou escala |
| B. Horário com calendário vazio | `Tem horario amanha?` | Nenhum horário sintético; pede espera ou escala |
| C. DDD x texto (prévia Fase 2) | número `5516...` + `Quero atender em Pato Branco` | Unidade = Pato Branco (texto vence DDD) |
| D. Clínico | `Estou com muita dor depois do procedimento` | Escalonamento; sem conselho clínico (prévia Fase 5) |

---

## 5. Patches sugeridos (para Dev/DevOps/QA aplicarem no repo; nada foi alterado)

```powershell
# Patch 1 — validate_local_flow.ps1, logo após `python -m pytest -q`
if ($LASTEXITCODE -ne 0) { throw "pytest falhou (exit $LASTEXITCODE)" }

# Patch 2 — validate_local_flow.ps1, no lugar do -match "14h ou 09:00"
if ($turnResult.reply_text -match '\b([01]?\d|2[0-3])(:[0-5]\d|h([0-5]\d)?)\b') {
    throw "reply_text contém horário sem evidência de calendário"
}
# e, apenas nos casos A e B da seção 4:
if ($turnResult.can_assert_facts -eq $true) { throw "can_assert_facts=true sem evidência de MCP" }

# Patch 3 — validate_local_flow.ps1, corpo do catch do passo [1/4] (com o compose B)
throw "intent-service fora do ar. Rode: docker compose up -d intent-service"
```

---

## 6. Entradas do log (mais recente no fim)

| # | Data | Quem | Passo | Evidência / resultado | Status |
|---|---|---|---|---|---|
| L-001 | 2026-10-17 | Claude | V0 `delivery_checklist.json` | JSON válido; `delivery_name="exemplo"` (F-09) | ✅ |
| L-002 | 2026-10-17 | Claude | V0 `docker-compose.yml` (1º upload) | YAML válido; `postgres`, `n8n`; volumes `n8n-data`, `n8n-db` | ✅ |
| L-003 | 2026-10-17 | Claude | V0 variáveis do compose x `.env` | Usadas no compose antigo presentes no `.env` | ✅ |
| L-004 | 2026-10-17 | Claude | V0 diff `.env` x `.env.example` | Extras no `.env`: `N8N_ENCRYPTION_KEY`, `N8N_VERSION`, `POSTGRES_*`. Valores comuns iguais ao template (F-01, F-06, F-07) | ⚠️ |
| L-005 | 2026-10-17 | Claude | V0 arquivos referenciados | 12 caminhos não enviados (F-11); `WEBHOOK_URL` com `/webhook` (F-05) | ⚠️ |
| L-006 | 2026-10-17 | Wesley | Pré-checagem | `docker compose exec postgres psql -U n8n -d n8n -c "SELECT ... FROM workflow_entity"` → 2 workflows com o mesmo nome (1 ativo, 1 inativo). Ver L-012 | ⚠️ |
| L-007 | 2026-10-17 | Wesley | V1 pré-requisitos | Docker 29.6.1, Compose v5.3.0, Git 2.54.0, Python 3.14.6. `docker info`: Docker Desktop (WSL2), contexto `desktop-linux`, 2 containers rodando | ✅ |
| L-008 | 2026-10-17 | Wesley | V2 `.env` | Anexados `POSTGRES_USER`, `POSTGRES_PASSWORD`, `N8N_VERSION=2.30.4`, `N8N_ENCRYPTION_KEY` (extraída de `/home/node/.n8n/config` do container `n8n_dentist_whatsapp-n8n-1`). Corrige F-02 | ⚠️ |
| L-008b | 2026-10-17 | Wesley | V2 `.env` | `Select-String` confirma `WEBHOOK_URL` ainda com placeholder e `/webhook` (F-05). Listagem de nomes omitiu chaves com dígito (F-19) | ❌ |
| L-009 | 2026-10-17 | Wesley | V2 aplicar arquivos | 3× `Copy-Item "$d\..."` falharam (`$d` é placeholder). `docker-compose.yml`, `.env.example`, `.gitignore` **não** substituídos (F-13). `Remove-Item ... -ErrorAction SilentlyContinue` sem erro visível; os alvos nem constavam no `git status` | ❌ |
| L-010 | 2026-10-17 | Wesley | V2 compose | `docker compose config --services` → `postgres`, `n8n` (2, esperado 3). `docker compose config -q` sem erro (no compose antigo) | ⚠️ |
| L-011 | 2026-10-17 | Wesley | V3 subir stack | `up -d --build` → 2/2 `Running` (nada recriado). `ps -a`: `n8nio/n8n:latest` (criado há 23 h), `postgres:15` (3 meses), porta 5678 publicada, 5432 não publicada. Filtro de logs (3 min) sem matches: não prova saúde (F-03 não confirmado) | ⚠️ |
| L-012 | 2026-10-17 | Wesley | V6 prévia | `workflow_entity`: `XNTMmT56aUElo2ng` (inativo) e `j9ZLd2huqjyrghXf` (ativo), mesmo nome (F-14) | ⚠️ |
| L-013 | 2026-10-17 | Wesley | Estado do git | ~35 arquivos modificados e ~30 novos não versionados (`.cursor/`, `config/clinic|session|voice.json`, `docs/canonical|governance|sprints`, `mcp/`, `app/domains/*`, `tests/test_*`, `scripts/import_n8n_workflow.ps1`, `docker/`). `.pyc` versionados (F-17). Trabalho grande **sem commit** | ⚠️ |
| L-014 | 2026-10-17 | Wesley | Banco `clinica` | `psql -f /docker-entrypoint-initdb.d/00{1,2}_*.sql` → arquivo inexistente; `Get-ChildItem db\init` → caminho inexistente; `\dt` em `clinica` → banco não existe. Esperado: compose atual não monta `db/init` e a pasta não existe (F-20) | ❌ (fora do gate F1) |
| L-015 | 2026-10-17 | Wesley | V5 `/turn` | `Invoke-RestMethod` com `<TEXTO>` literal → conexão recusada. Serviço Python não estava rodando e o compose atual não tem `intent-service` | ❌ |
| L-016 | 2026-10-17 | Claude | V0 (2º lote) | Compose A, B e atual lidos e comparados (F-12). `_env` sem chaves duplicadas. Variáveis obrigatórias de B (`POSTGRES_PASSWORD`, `N8N_ENCRYPTION_KEY`) presentes no `.env`. Dockerfile.intent: `python:3.14-slim`, usuário não-root, `CMD python intent_service.py`, sem segredos | ✅ |
| L-017 | 2026-10-17 | Wesley | V2 gate de versão | `docker compose exec n8n n8n --version` → **2.30.4** (= `N8N_VERSION`). `docker compose images`: `n8nio/n8n:latest` (d1606a508b1e, 3 meses), `postgres:15` (c29ef248e25f). F-16 resolvido | ✅ |
| L-018 | 2026-10-17 | Wesley | V2 arquivos na raiz | `Get-ChildItem Dockerfile.intent, .dockerignore, docker-compose*.yml` → só `docker-compose.yml`. Os 3 arquivos do B ainda não estão no repo (F-13) | ❌ |
| L-019 | 2026-10-17 | Wesley | V5 pré-checagem do código | `app/interfaces/http/intent_service.py`: `_HEALTH_PATHS = {"/healthz", "/"}`; `run_server(host="0.0.0.0", port=None)` com `PORT` do ambiente (padrão 8001). Compatível com o healthcheck do B (F-15) | ✅ |
| L-020 | 2026-10-17 | Wesley | V6 URLs dos workflows | `XNTM…` inativo → `http://host.docker.internal:8001/classify`; `j9ZL…` ativo → `http://host.docker.internal:8001/turn`. F-14 revisado; F-08 confirmado | ⚠️ |
| L-021 | 2026-10-17 | Wesley | V2 nomes no `.env` (regex corrigida) | 22 variáveis, sem duplicatas. Presentes: `POSTGRES_USER/PASSWORD`, `N8N_VERSION`, `N8N_ENCRYPTION_KEY`, `TZ` (obrigatórias do B ok). Ausentes sem impacto: `PORT`, `BIND_ADDR`, `N8N_PROTOCOL`, `N8N_PROXY_HOPS` (têm default), `GOOGLE_CALENDAR_*` (Fase 3). Sobram `N8N_BASIC_AUTH_*` e `DB_POSTGRESDB_{DATABASE,USER,PASSWORD}`, ignoradas pelo B (F-03, F-06). F-19 resolvido | ✅ |
| L-022 | 2026-10-17 | Wesley | V2 gate de imagem | `docker pull n8nio/n8n:2.30.4` → digest `sha256:d1606a508b1e…`, igual ao prefixo do ID da imagem `latest` em uso (L-017). Mesma imagem; F-16 fechado | ✅ |
| L-023 | 2026-10-17 | Wesley | V3 subir stack | `docker compose up -d --build` → "up 2/2": `postgres` Running, `n8n` Started (11,2 s). Sem linha de build e sem `intent-service`: indica compose **antigo**. O texto colado veio misturado com a listagem de `workflows/` (3 arquivos), e os passos 0 a 3 do Passo 2 não aparecem na evidência (F-13 segue aberto) | ⚠️ |
| L-024 | 2026-10-17 | Claude | V0/V6 leitura estática | Lidos `intent_workflow.json`, `intent_workflow_simple.json`, `import_n8n_workflow.ps1`, `validate_local_flow.ps1`, `n8n_grounded_reply.py`, `config_loader.py`, `validate_delivery.py`, `classify_intent.py`. Workflow ativo: `POST /webhook/intent-webhook` com `{message, from}` → `/turn` com `whatsapp_number` → nó `Grounded Reply`; resposta via `lastNode` (JSON com `reply_text` e `next`), sem nó de envio ao WhatsApp (correto para a Fase 1). JSON tem `id: j9ZL…` (reimportação idempotente). Achados F-21 a F-30 | ⚠️ |
| L-025 | 2026-10-17 | Wesley | V2 diagnóstico | `docker compose config --services` → `postgres`, `n8n` (2). `docker-compose.yml:3` = `postgres:15`; sem `intent-service` nem `name:` → compose antigo, B **não** aplicado (F-13). `.env:7 WEBHOOK_URL=http://localhost:5678/` → F-05 resolvido. `n8n_before.dump` **ausente** → backup ainda não feito. A checagem de `Dockerfile.intent`/`.dockerignore` saiu truncada (linha colada em duas), sem evidência nova | ⚠️ |
| L-026 | 2026-10-17 | Wesley | V5 pré-checagem | `Get-NetTCPConnection -LocalPort 8001` sem resultado: porta livre, sem python órfão. `intent_service.py`: `/turn` aceita `whatsapp_number` ou `from`; `/classify` ainda existe. F-23 resolvido | ✅ |
| L-027 | 2026-10-17 | Wesley | V4 testes | `python -m pytest -q` → **33 passed in 2.21s**, exit code 0 (Python 3.14.6, host). F-30 não reproduzido | ✅ |
| L-028 | | | | | |

---

## 6. Rodada 5 — 2026-10-22 (agente Cursor, ambiente Linux sem Docker)

| ID | Data | Quem | Passo | Resultado | Status |
|---|---|---|---|---|---|
| L-029 | 2026-10-22 | Agente | V4 | `pytest` encontrou **8 falhas** (HEAD 4f151c6): `GoogleCalendarGateway` sintético devolvia horários e "dra em São Carlos" mesmo sem ferramenta; classificador não reconhecia "disponibilidade"/"dúvida"/HOF; resposta de escalonamento fora do template de voz | ❌ |
| L-030 | 2026-10-22 | Agente | V4 | Correção: gateway padrão vazio, `tool_status` no contrato, classificador e voz ajustados. `pytest` → 53 passed; `python -m scripts.run_scenarios` → 15/15; `npm run test:console` → 12/12 | ✅ |
| L-031 | 2026-10-22 | Agente | V0 | `docker-compose.yml`: serviço `evolution-api` estava fora de `services:` (YAML inválido para o Compose) e com chave literal. Corrigido e parametrizado; `npm run validate` valida os três compose | ✅ |
| L-032 | 2026-10-22 | Agente | V6 | Auditoria estática do workflow: Code node com triagem/slots/reserva, calendar_id fixo, nome de nós com mojibake. Registrado em RAID e card A2 | ⚠️ |
| L-033 | 2026-10-22 | Agente | V3/V7 | Docker indisponível neste ambiente: n8n, webhook e Evolution API **não validados** (probes simulados em teste com servidor falso). Pendente para o Wesley rodar o Console localmente | ⏳ |

