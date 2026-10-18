# Local primeiro, pronto para a nuvem

A stack é a mesma nos dois ambientes: **n8n + serviço Python (intent/turn) + Postgres**, definida em `docker-compose.cloud-ready.yml`. O que muda de local para nuvem é o `.env` e o que fica na frente (túnel ou proxy HTTPS), não o código nem os workflows.

Regras que mantêm isso verdadeiro:

- Configuração só por variável de ambiente; nada de senha ou URL fixa no compose ou no workflow.
- Os serviços se falam pelo nome (`postgres`, `intent-service`), nunca por `localhost` ou `host.docker.internal`.
- A imagem do serviço Python não leva segredos (`.dockerignore` barra `.env`).
- Agenda e presença da dra continuam no Google Calendar; o Postgres guarda só estado de conversa e dados do n8n.

## Migrar do compose atual para este (uma vez)

Rode os comandos na pasta do projeto, em PowerShell, **antes** de parar o compose atual.

1. **Backup** (gera o arquivo dentro do container e copia, para evitar problema de codificação do PowerShell):
   ```powershell
   docker compose exec postgres sh -c "pg_dumpall -U n8n > /tmp/backup.sql"
   docker compose cp postgres:/tmp/backup.sql ./backup_antes_da_migracao.sql
   ```
2. **Chave de criptografia do n8n.** Hoje o n8n gerou uma chave sozinho e guardou no volume. Sem a mesma chave no `.env`, as credenciais salvas não abrem (nem aqui, nem na nuvem):
   ```powershell
   docker compose exec n8n cat /home/node/.n8n/config
   docker compose exec n8n n8n --version
   ```
   Copie o valor de `encryptionKey` e anote a versão do n8n.
3. **Acrescente ao `.env`** (e confirme que ele não está no git):
   ```
   POSTGRES_PASSWORD=n8n
   N8N_ENCRYPTION_KEY=<valor de encryptionKey>
   N8N_VERSION=<versão do passo 2>
   WEBHOOK_URL=http://localhost:5678/
   ```
   `POSTGRES_PASSWORD=n8n` porque o volume atual foi criado com essa senha. Troque depois com `ALTER USER n8n PASSWORD '...'` e atualize o `.env`.
4. **Pare o compose antigo sem apagar dados** (não use `-v`) e suba o novo:
   ```powershell
   docker compose down
   docker compose -f docker-compose.cloud-ready.yml up -d --build
   ```
5. **Atualize o workflow.** No nó HTTP, troque `http://host.docker.internal:8001/...` por `http://intent-service:8001/<mesmo caminho>` (hoje `/turn`).
6. **Valide:** `curl http://127.0.0.1:8001/healthz`, um POST no webhook do n8n e `pytest`.

Depois de validar, renomeie o antigo para `docker-compose.legacy.yml` e o novo para `docker-compose.yml`, para os comandos simples (`docker compose up`, `exec`) continuarem funcionando.

## Mapa: local agora, nuvem depois

| Item | Agora (local) | Nuvem |
|---|---|---|
| Stack | Docker Desktop | o mesmo compose numa VM Linux com Docker |
| Entrada do WhatsApp | túnel (Cloudflare Tunnel ou ngrok) e `WEBHOOK_URL` | domínio com HTTPS e proxy reverso (Caddy ou Traefik); `N8N_PROTOCOL=https`, `N8N_PROXY_HOPS=1` |
| Segredos | `.env` fora do git | gerenciador de segredos do provedor, injetando as mesmas variáveis |
| Postgres | container + volume | Postgres gerenciado: ajustar `DB_POSTGRESDB_HOST`/`PORT`, ligar SSL (variáveis `DB_POSTGRESDB_SSL_*` do n8n); mesmos dois bancos (`n8n`, `secretaria`) |
| Workflows | `./workflows` no repo | igual; importar no n8n novo |
| Backup | `pg_dumpall` manual | backup agendado do provedor + dump periódico |

`WEBHOOK_URL` é a URL base (termina em `/`, sem `/webhook`): o n8n acrescenta `/webhook/<path>` sozinho.

## Checklist antes de ir para a nuvem

- [ ] `.env` fora do git (`git rm --cached .env` e `.env` no `.gitignore`)
- [ ] `N8N_VERSION` fixada e `POSTGRES_PASSWORD` forte
- [ ] `N8N_ENCRYPTION_KEY` guardada também fora do volume (sem ela, as credenciais não abrem)
- [ ] Portas 5678 e 8001 sem exposição pública; só o proxy HTTPS recebe tráfego
- [ ] `WEBHOOK_URL` e `N8N_HOST` apontando para o domínio
- [ ] Restauração de backup testada de verdade
- [ ] Dados de pacientes (LGPD): provedor, região, quem acessa e por quanto tempo guardar definidos
