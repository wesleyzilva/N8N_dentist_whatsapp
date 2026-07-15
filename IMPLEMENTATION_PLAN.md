# Plano de Implementação — Automação Agentic para Consultório Odontológico

## 1. Objetivo

Construir uma plataforma agentic, self-hosted e evolutiva para automação de confirmação de consultas, reagendamento, triagem leve e atendimento humanizado, utilizando n8n, LLM, Google Calendar e WhatsApp.

A abordagem será incremental, com foco em entregar valor rapidamente e reduzir risco operacional.

---

## 2. Princípios de execução

- Entregar valor em ciclos curtos com sprints.
- Priorizar soluções de alto impacto e baixa complexidade primeiro.
- Separar MVP, evolução e itens de longo prazo.
- Manter rastreabilidade entre negócio, tecnologia e agentes.
- Trabalhar com agentes de desenvolvimento e agentes de stakeholder para simular decisões de produto e operação.

---

## 3. Jornadas do projeto

O plano será guiado por jornadas de experiência e operação, em vez de apenas por features isoladas.

### Jornada 1 — Descoberta e agendamento
- Objetivo: captar interesse e transformar lead em consulta agendada.
- Entregáveis principais:
  - fluxo inicial de pré-qualificação;
  - coleta de dados essenciais;
  - registro de intenção de agendamento.

### Jornada 2 — Confirmação e lembrete
- Objetivo: reduzir faltas e no-shows com comunicação clara e oportuna.
- Entregáveis principais:
  - confirmação via WhatsApp;
  - lembretes automáticos;
  - rastreio de respostas e status.

### Jornada 3 — Reagendamento e cancelamento
- Objetivo: recuperar a agenda com mínima fricção para o paciente e a equipe.
- Entregáveis principais:
  - reagendamento automatizado;
  - cancelamento com notificação;
  - atualização automática do calendário.

### Jornada 4 — Atendimento humanizado e reativação
- Objetivo: oferecer experiência acolhedora e manter relacionamento com o paciente.
- Entregáveis principais:
  - triagem leve e escalation para humano;
  - mensagens empáticas;
  - reativação de pacientes inativos.

---

## 4. Matriz de prioridade vs complexidade

### Quadrante 1 — Alta prioridade / Baixa complexidade (fazer primeiro)

Itens que entregam impacto imediato com baixo esforço:

- Setup de infraestrutura base (Docker, .env, volumes, logs básicos).
- Workflow inicial de confirmação de consulta via WhatsApp.
- Templates de mensagem para confirmação e lembrete.
- Registro básico de eventos e status no n8n.
- Definição de critérios de aceite e checklist de QA.

### Quadrante 2 — Alta prioridade / Alta complexidade (dividir em sprints)

Itens críticos, mas que exigem execução gradual:

- Webhook de entrada e classificação de intenção com LLM.
- Integração com Google Calendar para atualização de eventos.
- Reagendamento e cancelamento automatizados.
- Escalonamento para atendimento humano.
- Persistência de dados e auditoria operacional.

### Quadrante 3 — Média prioridade / Baixa complexidade (próximo passo)

Itens úteis para maturação do sistema:

- Dashboard operacional simples.
- Templates customizados por perfil de paciente.
- Logs mais ricos e métricas de resposta.
- Fluxos de fallback com regras de segurança.

### Quadrante 4 — Baixa prioridade / Alta complexidade (postergar)

Itens importantes no futuro, mas não essenciais ao MVP:

- Campanhas avançadas de reativação e retargeting.
- Integração completa com marketing digital e Customer Match.
- Multi-clínica, multi-usuário e multi-provedor.
- Automação muito sofisticada de triagem médica.

---

## 5. Backlog priorizado por jornadas

### Jornada 1 — Descoberta e agendamento
- P0: fluxo inicial de pré-qualificação e registro de intenção
- P1: integração com canal de entrada de leads
- P2: enriquecimento de dados do paciente

### Jornada 2 — Confirmação e lembrete
- P0: workflow de confirmação via WhatsApp
- P0: envio de lembretes automáticos
- P1: rastreio de resposta e status
- P2: personalização de templates por contexto

### Jornada 3 — Reagendamento e cancelamento
- P0: reagendamento automatizado
- P0: cancelamento com notificação
- P1: atualização automática do calendário
- P1: fallback para equipe humana

### Jornada 4 — Atendimento humanizado e reativação
- P0: triagem leve e classificação de intenção
- P1: mensagens empáticas e contextuais
- P1: reativação de pacientes inativos
- P2: métricas de retenção e ROI

### Priorização geral
- P0: essencial para o MVP
- P1: melhora operação e confiabilidade
- P2: maturação e expansão

---

## 6. Plano por sprints e revisão contínua

### Papel central — Agile Delivery Manager Agent

Para garantir coerência entre estratégia, execução e comunicação, o projeto deve ter um agente global de gestão chamado Agile Delivery Manager Agent.

Este agente é responsável por:
- coordenar o plano geral com o Product Owner e o time de desenvolvimento;
- ajustar prioridades conforme mudanças de negócio, dependências e riscos;
- revisar o estado dos sprints e propor ações corretivas;
- consolidar feedback dos stakeholders e transformar isso em decisões acionáveis;
- manter o backlog, o RAID log e as métricas de progresso alinhados.

### Funções principais do Agile Delivery Manager Agent
- gerir a execução por jornadas e sprints;
- sincronizar Product Owner, stakeholders e time técnico;
- identificar bloqueios e dependências cedo;
- facilitar decisões de trade-off e replanejamento;
- garantir que o trabalho entregue reflita o valor real para o negócio.

### Como ele interage com o ecossistema
- com o Product Owner: alinhando prioridades e critérios de aceitação;
- com o time de desenvolvimento: organizando execução e removendo bloqueios;
- com os stakeholders: consolidando demandas, riscos e feedbacks;
- com o Architect: validando viabilidade técnica e impacto no plano.

---

## 7. RAID log de controle

Cada sprint deve terminar com uma revisão objetiva para responder:
- O que foi entregue?
- O que ficou em aberto?
- O que mudou no backlog?
- Quais riscos, dependências ou problemas surgiram?

### Ritual de revisão de sprint
- Revisão de execução: validar entregas e critérios de aceite.
- Revisão de backlog: mover itens entre backlog, em andamento, bloqueado e concluído.
- Revisão de RAID: atualizar riscos, assumptions, issues e dependencies.
- Retrospectiva: ajustar próximos passos com base na execução real.

### Sprint 0 — Fundação

### Sprint 0 — Fundação

Duração: 1 semana

Objetivo: preparar a base para desenvolvimento.

Entregas:
- Ambiente Docker funcionando.
- Estrutura do projeto alinhada com o monorepo sugerido.
- Regras de desenvolvimento, convenções e backlog iniciado.
- Definição de critérios de aceite para os fluxos principais.
- Setup inicial de agentes de desenvolvimento e stakeholder.

### Sprint 1 — MVP de confirmação

Duração: 1 a 2 semanas

Objetivo: colocar um fluxo simples de confirmação em operação.

Entregas:
- Workflow de confirmação no n8n.
- Integração básica com WhatsApp.
- Template de mensagem inicial.
- Registro básico de status da confirmação.

### Sprint 2 — Webhook e inteligência

Duração: 1 a 2 semanas

Objetivo: transformar respostas em ações automáticas.

Entregas:
- Webhook de entrada.
- Classificação de intenção com LLM.
- Roteamento por intenção: confirmar, reagendar, cancelar, dúvida.
- Primeiros testes com respostas reais de pacientes.

### Sprint 3 — Operação clínica

Duração: 1 a 2 semanas

Objetivo: cobrir os cenários mais comuns de operação.

Entregas:
- Fluxo de reagendamento.
- Fluxo de cancelamento.
- Atualização do evento no Google Calendar.
- Regras de fallback e notificação para equipe.

### Sprint 4 — Humanização e controle

Duração: 1 semana

Objetivo: tornar o sistema mais confiável e humano.

Entregas:
- Mensagens empáticas e contextuais.
- Escalonamento para atendimento humano.
- Logs de auditoria e rastreio de decisões.
- Regras de opt-out e limites operacionais.

### Sprint 5 — Métricas e maturidade

Duração: 1 a 2 semanas

Objetivo: transformar o fluxo em um sistema gerenciável.

Entregas:
- Dashboard básico de métricas.
- Indicadores de confirmação, no-show, reagendamento e ROI.
- Melhorias de prompt e avaliação de qualidade.

### Sprint 6 — Escala e produção

Duração: 1 a 2 semanas

Objetivo: preparar para uso mais robusto e expansão.

Entregas:
- Segurança e observabilidade.
- Deploy mais estável.
- Preparação para integração com marketing e reativação.
- Governança e documentação operacional.

---

## 7. RAID log de controle

O RAID log deve ser usado como ferramenta de governança para acompanhar o andamento do projeto.

### Estrutura recomendada
| Tipo | Descrição | Impacto | Mitigação | Responsável | Status |
|---|---|---|---|---|---|
| Risk | Evento que pode impedir ou atrasar a entrega | Alto / Médio / Baixo | Plano de contingência | Agent / Owner | Aberto / Em mitigação / Fechado |
| Assumption | Hipótese de negócio ou técnica que precisa ser validada | Alto / Médio / Baixo | Validação com evidência | Agent / Owner | Validado / Não validado |
| Issue | Problema já ocorrido | Alto / Médio / Baixo | Correção imediata | Agent / Owner | Aberto / Resolvido |
| Dependency | Dependência externa ou interna que pode bloquear avanço | Alto / Médio / Baixo | Plano de acompanhamento | Agent / Owner | Aberto / Resolvido |

### Regras de uso
- Atualizar o RAID log ao fim de cada sprint.
- Priorizar itens com impacto alto e status aberto.
- Escalar riscos críticos para o Product Owner e para o Architect.
- Manter o backlog alinhado ao que realmente está sendo entregue.

### Exemplos iniciais
- Risk: integração com provedor de WhatsApp pode ter latência ou limitação de webhook.
- Assumption: o fluxo de confirmação gera redução relevante de no-show.
- Issue: falta de template aprovado pode atrasar testes de UX.
- Dependency: configuração de credenciais Google/WhatsApp precisa ser concluída antes do fluxo completo.

---

## 8. Estrutura de agentes de desenvolvimento

### Agentes de execução e governança
- Agile Delivery Manager Agent
  - atua como hub de integração entre estratégia, execução e comunicação;
  - acompanha métricas de sprint e evolução do backlog;
  - ajusta o plano com base em fatos, riscos e feedbacks.

- Product Owner Agent
  - define prioridades e aceitação do que entra no sprint.

- Architect Agent
  - valida arquitetura e impacto técnico das decisões.

- Backend / Integration Agent
  - implementa integração e orquestração.

- Workflow Automation Agent
  - cuida dos fluxos n8n e automações.

- QA / Validation Agent
  - valida comportamento e qualidade.

- DevOps / Infra Agent
  - garante infraestrutura e ambiente estável.

- Security / Compliance Agent
  - insere controles de privacidade e compliance.

- Data / Analytics Agent
  - monitora métricas e indicadores de valor.

- Prompt / LLM Agent
  - ajusta prompts e qualidade do uso da IA.

---

## 9. Agentes stakeholder e pessoas agentic

Os agentes abaixo devem operar como uma força de execução coordenada para entregar o projeto.

### Agentes de desenvolvimento

- Product Owner Agent
  - Prioriza backlog.
  - Define critérios de aceitação.
  - Media conflitos entre negócio e tecnologia.

- Architect Agent
  - Define a arquitetura do fluxo e integração entre n8n, LLM, WhatsApp e Google Calendar.
  - Mantém consistência técnica.

- Backend / Integration Agent
  - Implementa workflows, integrações e APIs.
  - Cuida da orquestração de eventos e dados.

- Workflow Automation Agent
  - Especialista em n8n e automações.
  - Otimiza fluxos, retries, fallbacks e tratamento de erros.

- QA / Validation Agent
  - Testa cenários de confirmação, reagendamento, cancelamento e erros.
  - Garante qualidade e reprodutibilidade.

- DevOps / Infra Agent
  - Gerencia Docker, ambiente, volumes, deploy e observabilidade.

- Security / Compliance Agent
  - Cuida de consentimento, opt-out, proteção de dados e rastreabilidade.

- Data / Analytics Agent
  - Organiza métricas, logs e indicadores de desempenho.

- Prompt / LLM Agent
  - Ajusta prompts, classificação de intenção e qualidade das respostas.

---

## 9. Agentes stakeholder e pessoas agentic

Esses agentes simulam os principais papéis humanos de negócio e operação, permitindo que o Product Owner receba feedback estruturado e decisões mais rápidas.

### Stakeholder agents

- Clinic Owner Agent
  - Representa a visão do consultório.
  - Prioriza redução de no-show e ganho de eficiência.

- Front Desk / Secretary Agent
  - Representa a rotina de agendamento e comunicação.
  - Identifica gargalos operacionais reais.

- Patient Experience Agent
  - Foca na empatia, clareza e humanização da conversa.
  - Avalia se a mensagem é adequada e acolhedora.

- Clinical Triage Agent
  - Representa a necessidade de avaliação médica prévia.
  - Define critérios de prioridade clínica e segurança.

- Marketing / Retention Agent
  - Foca em reativação, relacionamento e geração de oportunidade.

- Finance / ROI Agent
  - Mede impacto financeiro, eficiência e retorno sobre investimento.

- Compliance / Privacy Agent
  - Avalia riscos regulatórios e regras de consentimento.

- Provider / Vendor Agent
  - Representa provedores de WhatsApp, Google e LLM.
  - Ajuda a lidar com limites, dependências e integração externa.

### Como esses agentes devem interagir com o Product Owner

- Cada agente entrega feedback em formato de requisito, risco ou sugestão de melhoria.
- O Product Owner Agent consolida essas entradas em decisões priorizadas.
- As decisões passam para o backlog e para os sprints.
- Em cada sprint review, os stakeholder agents validam se a solução atende ao objetivo de negócio.

---

## 10. Critérios de sucesso

O projeto estará em bom estado quando:

- O fluxo básico de confirmação estiver funcionando end-to-end.
- Respostas de pacientes forem interpretadas corretamente na maioria dos casos.
- Reagendamento e cancelamento forem tratados sem intervenção manual.
- O processo gerar logs e métricas confiáveis.
- A solução puder evoluir sem reescrever a base inteira.

---

## 11. Reorganização contínua do plano

O plano deve ser revisado sempre que uma nova entrega, mudança de prioridade ou bloqueio surgir.

### Regra de reordenação
Sempre que houver uma nova entrega, o Agile Delivery Manager Agent deve responder a 4 perguntas:
1. Qual é o valor de negócio dessa entrega?
2. Qual é a complexidade real de execução?
3. Quais dependências ou riscos ela cria?
4. O que precisa ser interrompido ou adiado para priorizar isso?

### Critério de atualização
- itens com maior valor e menor risco devem subir no backlog;
- entregas que dependem de terceiros devem ser observadas com atenção;
- itens já iniciados só devem mudar de posição se houver impacto claro no plano;
- cada reordenação deve ser registrada no backlog e no RAID log.

### Resultado esperado
O plano passa a funcionar como um mapa dinâmico de execução, mostrando sempre a próxima sequência lógica de trabalho.

---

## 12. Próximos passos imediatos

1. Definir o papel do Agile Delivery Manager Agent como ponto central de governança.
2. Criar o primeiro sprint review com entrada do Product Owner, time técnico e stakeholders.
3. Atualizar o backlog e o RAID log no fim de cada sprint.
4. Estabelecer uma rotina semanal de alinhamento e replanejamento.

---

## 13. Recomendação de governança

1. Definir o backlog inicial do Sprint 0.
2. Criar uma lista de tarefas por agente.
3. Iniciar o Sprint 0 com infraestrutura, ambiente e critérios de aceitação.
4. Começar o workflow de confirmação como primeiro entregável real.

---

## 12. Recomendação de governança

- Reunião semanal de alinhamento entre Product Owner, Architect e agentes de execução.
- Review ao fim de cada sprint com stakeholder agents.
- Atualização do backlog após cada sprint.
- Manter um quadro simples de status: backlog, em andamento, bloqueado, concluído.
