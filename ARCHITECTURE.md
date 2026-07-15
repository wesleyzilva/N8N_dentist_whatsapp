# Arquitetura Unificada — WhatsApp Reativação + VIPpocket + Admin

Resumo
- Objetivo: unificar `whatsappSenderHttp`, `VIPpocket` e `VIPpocket_adm` em uma plataforma com dados centralizados, eventos atribuíveis e regras operacionais (dedupe, opt-out, limites).
- Entrega deste documento: arquitetura, modelo de dados mínimo e contrato de endpoints REST/events.
- Posicionamento: o projeto deve ser agentic como a Gather, entregando atendimento humanizado para clínicas de harmonização orofacial com controle operacional e escalonamento humano.

Visão geral dos componentes
- `api` — Node.js (TypeScript) REST + event bus. Responsável por CRUD de clientes, registros de visita, controle de ciclos fidelidade, logs de disparo e orquestração de jobs.
- `whatsapp-engine` — motor de envio (Baileys/whatsapp-web.js) executado como worker; lê jobs da fila, aplica rate-limit/dedupe em Redis e envia mensagens.
- `pwa-client` — VIPpocket (Angular) para clientes; gera QR, cria/atualiza `Customer` via API.
- `admin` — VIPpocket_adm (Angular) painel do lojista; consome APIs para métricas e ação manual (carimbar, exportar).
- `exporter` — job que gera CSV SHA-256 para Google Ads Customer Match e/ou integra com Google Ads API.
- Infra: Postgres, Redis, Queue (BullMQ), Docker Compose / GH Actions.

Monorepo sugerido
- /packages/api
- /packages/whatsapp-engine
- /packages/pwa-client
- /packages/admin
- /packages/exporter
- /packages/service-layer
- /infra (docker-compose, envs)

Regras operacionais (resumo)
- Deduplicação: por telefone normalizado + janela por calendário (mês).
- Opt-out: `blacklist` central; verificada na seleção e no envio.
- Limites: cap diário por account e global; contadores atômicos em Redis.
- Horários: operação entre 08:00–20:00, Segunda–Sábado.
- Atendimento humanizado: mensagens modeladas para pacientes de harmonização orofacial, fallback automático para suporte humano, e classificação de sentimento/intenção para priorizar contatos.

Serviço agentic
- Agente proativo que gerencia lembranças de consulta, confirmações e reagendamentos.
- Fluxos de atendimento em duas camadas: primeira resposta automatizada com IA e segunda camada de escalonamento para equipe humana.
- Templates adaptáveis e acompanhamento contínuo para reforçar a experiência de cuidado e confiança.

Equipe agentic recomendada
- **Vendas e pré-qualificação:** identifica pacientes potenciais, classifica interesse e alimenta o funil de agendamento.
- **Secretaria digital:** automatiza confirmação, reagendamento e controle de slots disponíveis.
- **Triagem clínica:** coleta informações prévias, detecta necessidade de consulta presencial e valida prioridade de casos.
- **Suporte humanizado:** responde dúvidas de pacientes com mensagem empática e transita para atendimento humano quando indicado.
- **Marketing digital:** coordena presença em Instagram, Google Meu Negócio, Facebook e site, convertendo reputação em leads qualificados.
- **Reativação e Customer Match:** transforma a base de clientes inativos em público para campanhas de retenção e recuperação.
- **Compliance operacional:** aplica opt-out, limpa listas e garante limites de envio adequados por canal.
- **Analytics e ROI:** reporta métricas de frequência, ticket médio, custo de oportunidade e retorno sobre investimento.

Essa estrutura garante que o consultório atue de forma autônoma, mas com os papéis de um time completo suportados pela plataforma.

Modelo de dados mínimo (tabelas essenciais)
- customers
  - id (uuid)
  - phone (e.164)
  - email
  - name
  - created_at

- visits
  - id
  - customer_id
  - store_id
  - timestamp
  - source (qr|admin|landing)
  - value (decimal)

- loyalty_cycles
  - id
  - customer_id
  - start_at
  - visits_count
  - rule_size
  - reward_type
  - status

- transactions
  - id
  - visit_id
  - amount
  - currency

- dispatch_logs
  - id
  - customer_id
  - campaign_id
  - message_text
  - channel (whatsapp)
  - status (queued|sent|failed|skipped)
  - sent_at
  - account_id

- blacklist
  - phone
  - reason
  - created_at

- campaign_exports
  - id
  - date
  - file_path
  - google_job_id

APIs principais (contratos resumidos)
Autenticação: JWT para serviços; OAuth2 (Google) opcional para admin.

- POST /api/customers
  - Cria ou encontra cliente por `phone`.
  - Body: { phone, name?, email? }
  - Resposta: `{ customer }`
  - Produz evento: `customer.created` (quando novo)

- GET /api/customers/:id
  - Retorna `Customer` e status do ciclo de fidelidade.

- POST /api/visits
  - Registra visita (QR scan ou admin)
  - Body: { customer_phone | customer_id, store_id, timestamp?, value? }
  - Resposta: `{ visit }`
  - Produz evento: `visit.created` → atualiza `loyalty_cycle`, recalcula KPIs e notifica admin websocket

- GET /api/loyalty/:customer_id
  - Retorna ciclo atual e progresso.

- POST /api/dispatch/queue
  - Enfileira um job de dispatch (campanha)
  - Body: { campaign_id?, selector: { last_seen_gt?, tag?, min_value? }, message_template }
  - Valida blacklist/dedupe ao gerar jobs; cria `dispatch_logs` em estado `queued`.
  - Resposta: `{ job_id, queued_count }`

- POST /api/dispatch/run/:job_id
  - Endpoint operacional para forçar execução imediata (protegido).

- GET /api/dispatch/logs?customer_id=&campaign_id=
  - Lista logs de envio/audit.

- POST /api/blacklist
  - Body: { phone, reason }
  - Marca opt-out imediato; cancela qualquer job pendente para o número.

- GET /api/exports/customer-match?date=
  - Gera ou retorna CSV hashed para Google Ads.

Webhooks / Eventos
- webhook: POST /webhooks/ads/conversion
  - Recebe conversões do landing page para ligar tráfego pago → cliente
  - Body: { phone?, conversion_id, campaign, landed_at }
  - Produz evento `ads.conversion` vinculado a `customer` se phone presente

Fila / Worker behaviour
- `whatsapp-engine` consome jobs, para cada target:
  - Verifica blacklist
  - Verifica dedupe via Redis (phone+YYYYMM)
  - Incrementa contador diário atômico (Redis INCR) por `account_id`
  - Obedece janela horária e cap; se fora de janela requeue com delay
  - Registra resultado em `dispatch_logs` (status)

Sequência simplificada: QR → Visit → loyalty update → (option) enqueue re-engagement → dispatch worker → send → export Customer Match

Segurança & privacidade
- Hashing: telefones exportados para Google Ads devem ser SHA-256 (lowercase, without +). Fazer normalização E.164 antes do hash.
- Dados sensíveis: armazenar apenas o necessário; mascarar logs em UI; rotacionar chaves.
- Opt-out: operação imediata e irreversível para o número marcado; manter histórico de quando/quem marcou.

Observações de implementação rápidas
- Comece com API minimal e contrato OpenAPI/Swagger (gera stubs). Implementar `customers`, `visits`, `dispatch` e `blacklist` primeiro.
- Mapeie o fluxo atual do `whatsappSenderHttp` para a etapa de `dispatch/queue` (lista gerada por Python pode ser importada como CSV para /api/dispatch/queue).
- Atualizar `VIPpocket` e `VIPpocket_adm` para pointar ao endpoint `api` em vez do `localStorage` mock.

Próximos passos sugeridos
1. Gerar schema ERD e arquivo OpenAPI (contratos) para as APIs acima.
2. Scaffold mínimo do monorepo com `packages/api` (TypeScript + Express/Nest), `packages/whatsapp-engine` (worker stub), e `infra/docker-compose.yml`.
3. Migrar CSV-based pipeline existente para um import endpoint temporário para acelerar adoção.

Arquivo criado por automação — se quiser, gero agora o OpenAPI e o ERD (opção: OpenAPI ou scaffold). Qual prefere agora?
