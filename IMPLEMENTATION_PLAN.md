# Fases de implementação — agentic TPM

Ordem fixa. Não pular fase: a seguinte depende da evidência da anterior.
Mapa: `docs/canonical/CANONICAL_MAP.md`. Gates: `docs/governance/PHASE_GATES.md`.

## Fase 0 — Governança (feita)

- Mapa canônico, RACI, RAID, rules/skills Cursor, contratos MCP
- Clínica 46/16 em `config/clinic.json`
- Guardrails de grounding
- Critério: TPM consegue abrir um card de sprint apontando P1–P10 sem inventar escopo

## Fase 1 — Canal e voz (P1, P10) (em andamento — domínio/HTTP prontos; import n8n pendente)

- Webhook WhatsApp estável no n8n
- Classificador + templates humanizados
- Estado mínimo da conversa
- Critério: mensagem de confirmação/dúvida recebe resposta no tom da secretária, sem fatos inventados

## Fase 2 — Unidade e presença (P3, P4)

- Resolver DDD 46 / 16 e cidade no texto
- Presença da dra só via evidência de calendário/bloco
- Critério: “a dra está em Pato Branco?” nunca é respondido sem tool; DDD 16 não força São Carlos se o texto disser Pato Branco

## Fase 3 — Agenda grounded (P2, P5)

- MCP Google Calendar: freebusy por unidade
- SecretaryVoice só cita slots retornados
- Critério: se o calendário falhar, a resposta pede espera ou escala; zero horários sintéticos

## Fase 4 — Mutação de agenda (P6)

- Confirmar, reagendar, cancelar com confirmação explícita do paciente
- Dual-write: evento Google + status no n8n
- Critério: nenhuma mutação sem intent CONFIRM explícito no turno

## Fase 5 — Triagem e humana (P7, P8)

- Regras de escalonamento (dor, emergência, menor, reclamação, baixa confiança)
- Handoff com resumo factual
- Critério: caso clínico não recebe conselho automatizado

## Fase 6 — Compliance e produção (P9)

- Opt-out, auditoria, horários de operação, observabilidade
- Critério: QA reproduz o fluxo com evidência; Security assina o gate

## Como o TPM usa isto

1. Escolher um ID P*
2. Abrir sprint card (`SPRINT_CARD_TEMPLATE.md`) com fase e gate
3. Atribuir `dev-agentic` + `qa-agentic` (e voz/security se P1/P9)
4. Dev só implementa contra MCP/schema existente
5. QA valida grounding (não só “o workflow rodou”)
6. Atualizar RAID ao fechar a fase


Primeiro focar no codigo para fazer as integrações e depois olhar para o frontend.
Plano Mestre de Implementação e Roteiro de Testes: SecretarIA Dra. Daiana
Este plano consolida o panorama completo do projeto: tudo o que já foi realizado, o que falta fazer (com foco na gravação real de consultas no Google Calendar e conexão do WhatsApp) e a bateria de testes integrados (executáveis tanto pela interface web construída quanto por scripts no terminal).
📌 1. Panorama Geral: O Que Já Fizemos
Componente	O Que Foi Concluído	Status
Google Calendar OAuth2	Credencial criada e autorizada no container n8n (197545539153-...). Calendário da clínica configurado (b7f9f29c5e...group.calendar.google.com).	🟢 Concluído
Microserviço Python Local	Gateway de calendário (calendar.py), classificador de intenções (intent_classifier.py) e regras de triagem/escalonamento (turn.py) implementados.	🟢 Concluído
Testes Conversacionais (Turnos)	Teste automatizado (testar_secretaria_ia.py) validando detecção de parente/filho, exibição de horários reais (22/10 09:00, 14:30, 16:00) e escalonamento para plano Bradesco/reembolso.	🟢 Concluído
Cérebro Gemini 3.8 Flash	Modelo oficial conectado via SDK @google/genai e via REST. Diagnóstico de retorno HTTP 429 (limite de taxa/cota no projeto gratuito) identificado e mapeado.	🟢 Concluído
Painel Web de Conexões	Testador ao vivo da API do Google Gemini com campo para validação imediata de chaves e visualização de tempo de resposta.	🟢 Concluído
Simulador Web de Atendimento	Chat interativo simulando WhatsApp com a persona humanizada da Dra. Daiana (Odontologia Ipanema) e badges de contexto (triagem de parentes, checagem de agenda).	🟢 Concluído
Matriz e Gerador de .env	Mapeamento das variáveis essenciais com exportação de .env pronto para o docker-compose.	🟢 Concluído
🎯 2. O Que Falta Fazer (Próximos Passos Prioritários)
Prioridade 1: Gravação Real de Consultas no Google Calendar (Write/Booking)
Implementar método book_appointment no Gateway do Calendar:
Criar chamada à API do Google Calendar (POST https://www.googleapis.com/calendar/v3/calendars/{calendarId}/events).
Parâmetros:
summary: Consulta Odontológica: {Nome do Paciente}
description: Paciente: {Nome} | Procedimento: {Motivo} | Responsável: {Nome Responsável} | WhatsApp: {Telefone}
start: Data e hora em formato ISO-8601 com timezone America/Sao_Paulo.
end: Início + 30 ou 45 minutos.
Adicionar Nó de Gravação no Fluxo do n8n:
Conectar nó Google Calendar (Operação: Create Event) após a confirmação expressa do paciente.
Retornar o link do evento criado e mensagem de confirmação humanizada com instruções de chegada à clínica.
Prioridade 2: Conexão Oficial WhatsApp via Meta Cloud API / n8n
Ativar o Webhook de Entrada:
Configurar o endpoint no n8n (/webhook/intent-webhook) para receber os payloads de mensagem da Meta.
Tratar mensagens de texto recebidas e extrair o número de telefone e nome do remetente.
Adicionar Nó de Resposta Oficial:
Utilizar o nó oficial WhatsApp do n8n para enviar a resposta de volta ao WhatsApp do paciente em menos de 3 segundos.
Prioridade 3: Gestão da Chave Gemini (Zerar Cota 429)
Criar chave em um "Novo Projeto" no Google AI Studio para renovar a cota gratuita ou habilitar plano com billing vinculado.
🧪 3. Roteiro de Testes Integrado (Web + Terminal)
Bateria de Testes A: Diretamente na Página Web Construída

Teste A.1: Validação de Conexão com Google Gemini
Onde: Aba "Conexões" no topo da página.
Ação: Clicar no botão "Testar Conexão com Gemini Agora".
Critério de Sucesso: Receber o status em tempo real com o código de resposta da API do Google e confirmação de conectividade.

Teste A.2: Teste de Nova Chave de API
Onde: Campo de texto na aba "Conexões".
Ação: Colar uma nova chave gerada no AI Studio e clicar em "Validar Esta Chave".
Critério de Sucesso: Feedback verde 🟢 Conexão com Google Gemini 3.8 Flash aprovada e ativa!.

Teste A.3: Simulação de Atendimento com Triagem de Parente
Onde: Aba "Diagnósticos / Simulação".
Ação: Enviar a mensagem: "Olá! Gostaria de agendar uma consulta para o meu filho Arthur nesta quinta-feira à tarde. Meu nome é Wesley."
Critério de Sucesso: A IA acolhe com o tom humanizado da Odontologia Ipanema, identifica que o paciente é o Arthur e apresenta opções de horários.

Teste A.4: Simulação de Escalonamento de Convênio / Reembolso
Onde: Aba "Diagnósticos / Simulação".
Ação: Enviar a mensagem: "Vocês atendem pelo plano Bradesco ou emitem nota para reembolso?"
Critério de Sucesso: A IA esclarece a emissão de nota para reembolso ou aciona o badge de escalonamento prioritário para a equipe da clínica.
Bateria de Testes B: Scripts Automatizados no Terminal Python

Teste B.1: Teste Direto de Conexão com Gemini
Comando: python testar_gemini.py
Critério de Sucesso: Resposta positiva de saudação gerada pelo modelo sem erro de importação de pacote.

Teste B.2: Teste do Fluxo Conversacional Multi-Turno da Secretária
Comando: python testar_secretaria_ia.py
Critério de Sucesso: Execução dos 3 turnos (triagem, oferta de horários e escalonamento) com sucesso no terminal.

Teste B.3: Teste de Criação Real de Evento no Google Calendar
Comando: python testar_agendamento_calendar.py
Critério de Sucesso: Evento teste criado com sucesso no calendário b7f9f29c5e... e conferência visível no Google Calendar da clínica.
🚀 4. Como Executar Agora
Abra a página web da aplicação em seu navegador.
Na aba "Conexões", verifique a matriz e teste sua chave do Gemini.
Na aba "Diagnósticos / Simulação", realize interações de teste com a SecretarIA.
Quando aprovado, avançaremos para o script de gravação real de eventos no Google Calendar.