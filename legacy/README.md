# Legacy — não usar em produção

Código anterior à reestruturação agentic. Mantido para consulta e reuso pontual. Nada aqui é importado por `app/`.

| Arquivo | O que era | Destino |
|---|---|---|
| `intent_service_legacy.py` | Serviço HTTP antigo com agenda sintética e `can_assert_facts` sempre `true` (viola o grounding) | arquivar |
| `intent_classifier.py` + `test_intent_classifier.py` | Classificador híbrido regras+LLM, 37 testes (`cd legacy && python -m pytest`). Intents `HOURS`/`CITY` divergem do contrato `AVAILABILITY`/`LOCATION` | avaliar reuso de ideias (limites de palavra, saída LLM validada) |
| `auth_e_agenda.py` | Fluxo OAuth local do Google Calendar | reusar na Fase 3 (A5) |
| `testar_secretaria_ia.py`, `simular_conversas.ps1`, `integrations_status.py` | Smokes e flags de integração | substituídos pelo TPM Console |
| `backup_XNTM.n8n-workflow.json` | Export do workflow n8n | arquivar |

O inventário completo e as decisões estão em `docs/governance/status.json` (`inventory`).
