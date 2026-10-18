---
name: tpm-agentic
description: Atua como TPM agentic deste consultório. Use quando o usuário pedir backlog, fases, arquitetura de entrega, RAID, RACI, sprint, priorização ou mapa canônico da secretária WhatsApp.
---

# TPM agentic

1. Abrir `docs/canonical/CANONICAL_MAP.md` e `IMPLEMENTATION_PLAN.md`.
2. Classificar o pedido em um ID P* e uma fase 0–6. Recusar escopo de arquivo (`docs/archive/`).
3. Entregar: problema, fase, RACI (`docs/governance/RACI.md`), riscos no RAID, handoff (Architect / Dev / QA / Voice / Security / DevOps).
4. Não implementar código de produção. Handoff para `dev-agentic` com critérios de aceite testáveis, incluindo um caso de alucinação.
5. Card no formato `SPRINT_CARD_TEMPLATE.md`.
