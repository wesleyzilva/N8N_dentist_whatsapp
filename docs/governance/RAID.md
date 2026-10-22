# RAID inicial

Atualizar ao fechar cada fase. Status: Aberto | Mitigando | Fechado.

| Tipo | Item | Impacto | Mitigação | Owner | Status |
|---|---|---|---|---|---|
| Risk | LLM inventa horário se o n8n pular grounding | Alto | `/turn` aplica grounding antes da voz; testes P2 no pytest | Architect | Mitigando |
| Risk | DDD do paciente confundido com cidade da dra | Alto | Separar Location vs Presence no código | Dev | Aberto |
| Risk | Dois calendários (46 e 16) dessincronizados | Alto | `clinic.json` com calendar_id por unidade; MCP único | Architect | Aberto |
| Risk | Provedor WhatsApp / webhook instável | Médio | Retry n8n + fila; Fase 1 com stub | DevOps | Aberto |
| Assumption | Dra alterna Pato Branco e São Carlos e isso está no Google Calendar | Alto | Validar com dona na Fase 2 | TPM | Não validado |
| Assumption | Paciente do 46 em geral quer a unidade de Pato Branco | Médio | Sempre confirmar cidade na primeira visita | Voice | Não validado |
| Risk | Copy ou LLM tratar o Zap como dentista geral e inventar procedimento/preço | Alto | `practice` em `clinic.json`; nunca `procedure_details` sem evidência | Voice | Mitigando |
| Issue | `ARCHITECTURE.md` antigo descrevia VIPpocket | Médio | Arquivado; mapa canônico substitui | TPM | Resolvido nesta entrega |
| Dependency | OAuth Google Calendar por calendário | Alto | Credenciais na Fase 3; mock até lá | DevOps | Aberto |
| Dependency | Número WhatsApp e janela 24h | Alto | Definir provedor antes do go-live Fase 1 | TPM | Aberto |
| Issue | Gateway de calendário padrão devolvia horários e "dra em São Carlos" sintéticos (8 testes vermelhos, violava o grounding) | Alto | `MissingCalendarGateway` volta a devolver vazio; Error/Fixture só em simulação; suíte de cenários P2/P4/P5 | Dev | Resolvido 2026-10-22 |
| Issue | Chave da Evolution API estava literal no `docker-compose.yml` e no histórico do git (serviço removido; WhatsApp agora é Meta Cloud API) | Alto | Rotacionar a chave antiga (A3); segredos Meta só no `.env` | Security | Mitigando |
| Risk | `N8N_ENCRYPTION_KEY` com valor padrão embutido no compose | Alto | Exigir a variável no `.env` (como no compose cloud-ready) após conferir o volume atual | DevOps | Aberto |
| Issue | Duas unidades usam o mesmo `google_calendar_id` em `config/clinic.json` | Alto | Obter um calendário por unidade (A4) antes da Fase 3; sem isso P4 não deriva presença por unidade | TPM | Aberto |
| Risk | Code node do workflow n8n concentra triagem, slots e reserva (regra de negócio no canvas) | Alto | Mover para `app/` e deixar o canvas só orquestrar (A2); reserva só na Fase 4 | Architect | Aberto |
| Risk | Palavra "dor" casa por substring no classificador e no turno (falso positivo escala; viés seguro) | Baixo | Limite de palavra mantendo recall (A7) | Dev | Aberto |
| Risk | Pedido de humana sai com motivo `clinical` no handoff | Médio | Motivos distintos (A6) | Dev | Aberto |
| Assumption | Workflow n8n e webhook da Meta funcionam ponta a ponta | Alto | Validar com o Console (aba Integrações + cenários contra n8n) quando o stack subir | DevOps | Não validado |
