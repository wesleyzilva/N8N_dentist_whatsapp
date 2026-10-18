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
