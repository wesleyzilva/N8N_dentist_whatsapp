# Próximos passos

## Feito (Fase 0)
- Mapa canônico P1–P10, arquitetura de secretária (não VIPpocket)
- Fases 0–6, RACI, RAID, gates
- Agentes Cursor (TPM, Architect, Dev, QA, Voice, Security, DevOps)
- Contratos MCP; clínicas 46/16; grounding no domínio

## Feito nesta entrega (Fase 1 — canal e voz)
- `POST /turn`: intent + hipótese de unidade + grounding + `reply_text`
- Workflow n8n chama `/turn` (path `intent-webhook`)
- Voz só com claims permitidas (`config/voice.json`)
- QA: round-trip HTTP + calendário vazio não inventa horário
- Prática canônica: harmonização orofacial (não odontologia geral); sem procedimento/preço inventado

## Agora (fechar gate da Fase 1 no n8n)
1. Subir o serviço (`python intent_service.py`) e o Compose
2. Importar `workflows/intent_workflow.json` e POSTar no webhook
3. Conferir que a resposta ao paciente é `reply_text`, nunca um horário solto no canvas

## Em seguida (Fase 2)
- Confirmar cidade quando a fonte for só DDD
- Presença da dra bloqueada até MCP de calendário (Fase 3)

Comando: `pytest`
