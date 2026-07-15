# Automação Agentic de Confirmação de Agendamentos — n8n + LLM + Google Calendar + WhatsApp

## Descrição Geral

**Problema de negócio:** altas taxas de no-show e faltas em consultórios odontológicos, especialmente em clínicas de harmonização orofacial, reduzem receita e sobrecarregam a gestão de agenda.

**Solução técnica proposta:** pipeline de hiperautomação self-hosted que utiliza `n8n` (orquestrador), Google Calendar como fonte de eventos, um modelo de linguagem (LLM) para interpretar e classificar respostas de pacientes, e uma API de WhatsApp para envio/recebimento de mensagens. A solução automatiza: disparo de confirmações, captura de respostas via webhook, processamento semântico com IA e atualização automática do evento no Google Calendar (ex.: mudar cor do evento para verde ao confirmar).

**Posicionamento agentic e humanizado:** o sistema atua como um assistente proativo para clínicas de harmonização orofacial, gerando mensagens com tom humano, escutando respostas com sensibilidade e escalando casos complexos para atendimento humano quando necessário. O fluxo entrega uma experiência conversacional próxima de um concierge de atendimento, ao mesmo tempo em que mantém controle operacional e compliance.

## Equipe Agentic

Para um consultório funcionar de forma autônoma e de alto impacto, a solução deve suportar múltiplos agentes digitais coordenados entre si:

- **Vendas / Pré-qualificação:** captura leads, apresenta serviços de harmonização orofacial e converte interesse em agendamento.
- **Secretaria / Agendamento:** agenda consultas, confirma horários e gerencia reagendamentos automaticamente.
- **Triagem clínica:** identifica casos que precisam de avaliação médica prévia, solicita informações adicionais e encaminha para equipe de diagnóstico.
- **Atendimento Humanizado:** responde dúvidas de pacientes com tom empático e transfere casos complexos para o time humano quando necessário.
- **Reativação / Retargeting:** reaproveita a base de pacientes inativos, reinicia contatos e alimenta campanhas do Google Ads com Customer Match.
- **Marketing digital:** coordena presença em Instagram, Google Meu Negócio, Facebook e site, transformando reputação em leads e apoiando ações de venda.
- **Operações / Compliance:** aplica regras de opt-out, limites de envio, deduplicação e mantém logs auditáveis.
- **Analytics / ROI:** monitora frequência de retorno, valor médio de cliente e eficiência do programa de acompanhamento.

Este ecossistema de agentes garante que o consultório não dependa de um único ponto de contato e que cada disciplina operacional seja representada pelo fluxo certo.

## Arquitetura da Solução

A solução é dividida em duas esteiras principais:

- **Esteira 1 — Disparo Ativo de Confirmações**
  - `n8n` executa um trigger/poll no Google Calendar para identificar eventos que exigem confirmação.
  - Gera mensagem padrão e envia via API de WhatsApp.
  - Persiste metadata (estado da confirmação) no próprio evento ou em um banco auxiliar.

- **Esteira 2 — Webhook de Captura e Processamento com IA**
  - Resposta do paciente chega por webhook ao `n8n` (provedor WhatsApp → webhook).
  - Um nó LLM (OpenAI/Anthropic via chamada HTTP ou LangChain) classifica intenção: CONFIRM, RESCHEDULE, CANCEL, QUESTION, UNKNOWN.
  - Roteamento condicional atualiza o Google Calendar:
    - CONFIRM → Atualiza evento (cor verde / tag "Confirmado").
    - RESCHEDULE → Inicia fluxo de reagendamento.
    - CANCEL → Cancela/abre o horário e notifica a equipe.

### Diagrama de fluxo (Mermaid)

```mermaid
flowchart LR
  subgraph Esteira_1 [Esteira 1 — Disparo Ativo]
    GC_TRIGGER[Google Calendar\nTrigger / Poll]
    FILTER[Filtrar eventos\n(próximos X dias)]
    MSG_PREP[Gerar mensagem\n(template)]
    WHATSAPP_SEND[API WhatsApp\nEnviar mensagem]
    GC_META[Persistir metadata\n(no DB / evento)]
    GC_TRIGGER --> FILTER --> MSG_PREP --> WHATSAPP_SEND --> GC_META
  end

  subgraph Esteira_2 [Esteira 2 — Webhook + IA]
    WHATSAPP_WEBHOOK[Webhook de entrada\n(WhatsApp → n8n)]
    ROUTER[Switch / Roteamento]
    LLM_NODE[LLM (OpenAI/Anthropic)\nClassificação de intenção]
    ACTION_CONFIRM[Atualizar Google Calendar\n(mudar cor → verde / tag=Confirmado)]
    ACTION_RESCHEDULE[Fluxo de Reagendamento]
    ACTION_CANCEL[Cancelar / Notificar equipe]
    WHATSAPP_WEBHOOK --> ROUTER
    ROUTER -- "Resposta: confirmar" --> LLM_NODE --> ACTION_CONFIRM
    ROUTER -- "Resposta: reagendar" --> LLM_NODE --> ACTION_RESCHEDULE
    ROUTER -- "Resposta: cancelar" --> LLM_NODE --> ACTION_CANCEL
    ACTION_CONFIRM --> GC_UPDATE[Google Calendar\nAPI Update Event]
    GC_UPDATE --> GC_META2[Persistir metadata]
  end

  %% Conexão entre esteiras
  GC_META --- GC_META2
  WHATSAPP_SEND -->|Recebe resposta| WHATSAPP_WEBHOOK
```

## Stack Tecnológica

- **Orquestração:** `n8n` (self-hosted via Docker)
- **Containerização:** `Docker` + `docker-compose`
- **Calendário:** Google Calendar API
- **IA / LLM:** OpenAI / Anthropic (via chamadas HTTP ou LangChain no `n8n`)
- **Mensageria:** API de WhatsApp (ex.: WhatsApp Business API, Twilio, Gupshup, Zenvia)
- **Persistência (opcional):** PostgreSQL ou SQLite para metadados
- **Infra / TLS:** Nginx ou Traefik como reverse-proxy, Let's Encrypt para certificados
- **Atendimento Humanizado:** fluxos de fallback para equipe humana e templates personalizados para harmonização orofacial

## Requisitos e Instalação

**Pré-requisitos**

- Docker e Docker Compose
- Projeto no Google Cloud com Google Calendar API habilitada
- Credenciais/Token para provedor de WhatsApp
- Chave de API para provedor LLM (OpenAI/Anthropic)

### Exemplo `docker-compose.yml` (básico)

```yaml
version: "3.8"
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: n8n
      POSTGRES_PASSWORD: n8n
      POSTGRES_DB: n8n
    volumes:
      - n8n-db:/var/lib/postgresql/data
    restart: unless-stopped

  n8n:
    image: n8nio/n8n:latest
    ports:
      - "5678:5678"
    environment:
      - DB_TYPE=postgresdb
      - DB_POSTGRESDB_HOST=postgres
      - DB_POSTGRESDB_PORT=5432
      - DB_POSTGRESDB_DATABASE=n8n
      - DB_POSTGRESDB_USER=n8n
      - DB_POSTGRESDB_PASSWORD=n8n
      - N8N_BASIC_AUTH_ACTIVE=true
      - N8N_BASIC_AUTH_USER=${N8N_BASIC_AUTH_USER}
      - N8N_BASIC_AUTH_PASSWORD=${N8N_BASIC_AUTH_PASSWORD}
      - N8N_HOST=${N8N_HOST:-localhost}
      - N8N_PORT=5678
      - WEBHOOK_URL=${WEBHOOK_URL}
      - GENERIC_TIMEZONE=${TZ:-Etc/UTC}
    volumes:
      - n8n-data:/home/node/.n8n
    depends_on:
      - postgres
    restart: unless-stopped

volumes:
  n8n-data:
  n8n-db:
```

Comando para iniciar:

```bash
docker compose up -d
```

Observações:

- Em produção, exponha `n8n` via proxy reverso com TLS e defina `WEBHOOK_URL` para a URL pública.
- Para desenvolvimento rápido, use `ngrok` e defina `WEBHOOK_URL` para o URL HTTPS gerado.

## Instruções resumidas de configuração

1. **Google Calendar API**
   - Crie projeto no Google Cloud Console e habilite a Google Calendar API.
   - Configure OAuth consent screen e crie credenciais OAuth 2.0 (Client ID / Client Secret).
   - No `n8n`, adicione credencial Google OAuth2 com escopo `https://www.googleapis.com/auth/calendar`.
   - Alternativa: **Service Account** para acesso programático (compartilhe o calendário com o e-mail da service account).

2. **WhatsApp API**
   - Obtenha token/endpoints do provedor escolhido.
   - Configure nó HTTP ou integração nativa no `n8n` para envio de mensagens.
   - Configure o webhook de recebimento no painel do provedor apontando para `WEBHOOK_URL`.

3. **LLM (OpenAI / Anthropic)**
   - Gere sua chave de API.
   - Use nó HTTP no `n8n` ou integração LangChain para chamadas ao LLM.
   - Padronize prompts para classificação e geração de respostas.

4. **Variáveis essenciais**
   - `WEBHOOK_URL` público para receber mensagens.
   - `N8N_BASIC_AUTH_USER` / `N8N_BASIC_AUTH_PASSWORD` para proteger a UI.
   - Configurar `DB_*` conforme `docker-compose.yml`.

## Variáveis de Ambiente (exemplo de `.env`)

```env
# n8n basic auth
N8N_BASIC_AUTH_USER=admin
N8N_BASIC_AUTH_PASSWORD=changeme

# Host / Webhook
N8N_HOST=example.com
WEBHOOK_URL=https://example.com/webhook

# Postgres (se aplicável)
DB_TYPE=postgresdb
DB_POSTGRESDB_HOST=postgres
DB_POSTGRESDB_PORT=5432
DB_POSTGRESDB_DATABASE=n8n
DB_POSTGRESDB_USER=n8n
DB_POSTGRESDB_PASSWORD=n8n

# Google OAuth2
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=https://example.com/rest/oauth2-credential/callback

# LLM
OPENAI_API_KEY=sk-...
LLM_PROVIDER=openai  # openai | anthropic

# WhatsApp API
WHATSAPP_API_URL=https://api.whatsapp-provider.example/messages
WHATSAPP_API_TOKEN=your_whatsapp_token

# Timezone
TZ=America/Sao_Paulo
```

## Recomendações de Confiabilidade e Segurança

- Implementar retries com backoff para chamadas a serviços externos (WhatsApp, Google, LLM).
- Log e auditoria de eventos de confirmação para compliance e disputas.
- Monitoramento e alertas (uptime, falhas de webhook, latência de LLM).
- Gerenciamento de consentimento e opt-out para evitar bloqueios de provedores de mensageria.

## Exemplos de prompt para classificação de intenção (LLM)

- **Sistema:** "Você é um classificador que só retorna uma das palavras: CONFIRM, RESCHEDULE, CANCEL, QUESTION, UNKNOWN."
- **Input:** "Oi, vou confirmar minha consulta."
- **Output esperado:** `CONFIRM`

## Próximos passos

- Ajustar templates de mensagem e SLA de retries.
- Implementar e validar fluxos end-to-end no `n8n` (teste com ngrok em dev).
- Integrar provider de WhatsApp e validar webhooks.

----

Arquivo gerado automaticamente pelo assistente; revise credenciais e segredos antes de commitar.
