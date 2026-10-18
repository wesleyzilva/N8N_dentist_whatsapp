# RACI — secretária WhatsApp

R = responsável, A = aprova, C = consultado, I = informado.

| Entrega | TPM | Architect | Dev | QA | Voice | Security | DevOps |
|---|---|---|---|---|---|---|---|
| Mapa canônico / fase | A/R | C | I | I | C | C | I |
| Contrato MCP | C | A/R | C | C | I | C | I |
| Código domínio / HTTP | I | C | R | C | I | C | I |
| Workflow n8n | I | C | R | C | I | I | A |
| Copy / tom | C | I | I | C | A/R | C | I |
| Gate de fase | A | C | I | R | C | C | I |
| Produção / secrets | I | C | I | C | I | A | R |

Escalada: desacordo Dev vs QA → Architect; desacordo produto vs risco → TPM + Security.
