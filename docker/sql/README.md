# N8N Dentist WhatsApp

Base para o sistema de gestão da clínica: **PostgreSQL + n8n** em Docker, com o banco `clinica` (pacientes, profissionais, procedimentos, agendamentos, lembretes e histórico de WhatsApp).

```
.
├── docker-compose.yml
├── .env.example
└── db/init/
    ├── 001_create_clinica.sql   # cria o banco "clinica"
    └── 002_schema.sql           # tabelas, índices e triggers
```

O Postgres tem **dois bancos**: `n8n` (interno do n8n, ele mesmo gerencia) e `clinica` (os dados do seu sistema). Os workflows do n8n leem e gravam em `clinica` por meio do nó Postgres.

---

## Opção A: manter os containers atuais (recomendado)

Não mexe em nenhum dado existente. Os comandos abaixo são para **PowerShell**.

**1. Descobrir os nomes e a configuração dos seus containers**

```powershell
docker ps -a --format "table {{.Names}}\t{{.Image}}\t{{.Ports}}"
docker inspect NOME_DO_POSTGRES --format "{{json .Config.Env}}"
docker inspect NOME_DO_N8N --format "{{json .Config.Env}}"
```

Anote o usuário e a senha do Postgres. Veja também se o n8n já usa Postgres (`DB_TYPE=postgresdb`) ou o SQLite padrão. Os dois funcionam para este projeto.

**2. Colocar os dois containers na mesma rede**

```powershell
docker network create clinica_net
docker network connect clinica_net NOME_DO_POSTGRES
docker network connect clinica_net NOME_DO_N8N
```

**3. Criar o banco da clínica e as tabelas**

```powershell
cd E:\wesleyzilva\repo\N8N_dentist_whatsapp
Get-Content db\init\001_create_clinica.sql | docker exec -i NOME_DO_POSTGRES psql -U SEU_USUARIO -d postgres
Get-Content db\init\002_schema.sql         | docker exec -i NOME_DO_POSTGRES psql -U SEU_USUARIO -d postgres
```

**4. Criar a credencial no n8n** (Credentials → Postgres)

| Campo    | Valor                                                    |
|----------|----------------------------------------------------------|
| Host     | `NOME_DO_POSTGRES` (nome do container, **não** `localhost`) |
| Port     | `5432`                                                   |
| Database | `clinica`                                                |
| User / Password | os do seu Postgres                                |

---

## Opção B: subir tudo com docker compose

Útil para recriar o ambiente do zero ou em outra máquina.

1. `Copy-Item .env.example .env` e preencha o `.env`.
2. **Se você já tem um n8n com credenciais salvas**, use a mesma chave de criptografia dele. Sem ela, as credenciais antigas não abrem:
   ```powershell
   docker exec NOME_DO_N8N cat /home/node/.n8n/config
   ```
   Copie o valor de `encryptionKey` para `N8N_ENCRYPTION_KEY`. Em instalação nova, gere uma chave:
   ```powershell
   -join ((1..32) | ForEach-Object { '{0:x2}' -f (Get-Random -Maximum 256) })
   ```
3. Para **reaproveitar os volumes atuais**, descubra os nomes com `docker volume ls` e troque a seção `volumes:` do compose por `external: true` (há um exemplo comentado no arquivo). Pare os containers antigos antes, pois as portas 5432 e 5678 não podem ser usadas pelos dois ao mesmo tempo.
4. Suba:
   ```powershell
   docker compose up -d
   ```

Os scripts de `db/init` só rodam quando o volume do Postgres é criado vazio. Se o volume já tinha dados, aplique o passo 3 da Opção A manualmente.

---

## WhatsApp

- **Webhook público:** o WhatsApp precisa chamar o n8n de fora da sua máquina. Para testar, use um túnel (Cloudflare Tunnel ou ngrok) e coloque a URL em `WEBHOOK_URL`.
- **Canal:** a API oficial da Meta (nós de WhatsApp do n8n) ou uma ponte não oficial, como Evolution API ou WAHA. Cada uma muda os workflows, então decida antes de construí-los.

## Cuidados

- Dados de pacientes são **dados de saúde sensíveis** (LGPD). A porta 5432 está exposta só em `127.0.0.1`; não a abra para a rede.
- A coluna `aceita_whatsapp` guarda o consentimento. Os workflows devem respeitá-la antes de enviar lembretes.
- Backup do banco da clínica:
  ```powershell
  docker exec NOME_DO_POSTGRES pg_dump -U SEU_USUARIO clinica > backup_clinica.sql
  ```
