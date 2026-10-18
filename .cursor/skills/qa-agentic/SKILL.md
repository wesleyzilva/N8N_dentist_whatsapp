---
name: qa-agentic
description: QA agentic da secretária WhatsApp. Use para critérios de aceite, pytest, gates de fase, regressão de alucinação, DDD 46/16 e calendário indisponível.
---

# QA agentic

1. Gates em `docs/governance/PHASE_GATES.md`.
2. Matriz mínima: 46, 16, outro DDD, conflito texto/DDD, calendário down, pedido clínico, confirmação explícita.
3. Rodar `pytest` e recusar merge se grounding não tiver teste.
4. Evidência: comando, casos, P* cobertos, gaps. Sem “parece ok”.
