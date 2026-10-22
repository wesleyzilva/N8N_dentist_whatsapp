# Sprint — TPM Console e validação local

## Título
- [x] Frontend local para o TPM acompanhar fases, validar integrações/testes e simular conversas

## Descrição
- Fase 1 (gate) com apoio às Fases 2–6. IDs: P2 (não alucinar), P10 (orquestração); transversal a P1–P9 como evidência.
- Objetivo: um lugar fácil de operar (Node, sem dependências) que mostra o estado real do projeto e prova o grounding.
- Contexto: o HEAD tinha 8 testes vermelhos por agenda sintética; o TPM não tinha visão única de fases, testes e integrações.

## Critérios de aceite
- [x] `npm run console` abre painel com fases 0–6, P1–P10, backlog, RAID e inventário do que já temos
- [x] `npm run validate` roda pytest, cenários, config, MCP, workflows, compose, segredos, `.env`, higiene e integrações
- [x] Simulador de conversa com calendário vazio / com erro / fixture, contrato da resposta e lint de grounding
- [x] Suíte de cenários compartilhada entre pytest, CLI e Console (inclui os 3 gates anti-alucinação)
- [x] Caso "ferramenta vazia/erro" presente (S05, S06, S07, S08)
- [x] Segredos nunca exibidos; servidor só em 127.0.0.1 com cabeçalho anti-CSRF

## Dependências
- [x] Node 20+ e Python 3.10+ (pytest e pyyaml via `requirements-dev.txt`)
- [ ] Docker/n8n/Meta Cloud para validar integrações reais (probes prontos; stack não sobe neste ambiente de CI)

## Responsável
- Dev: Console, runner de cenários, correção do gateway
- QA: suíte de cenários e testes do Console
- TPM: `status.json` e leitura do Painel
- DevOps: compose corrigido

## Status
- [x] Concluído (código); validação das integrações reais depende do stack local

## Observações
- Evidência: pytest 53 passed; cenários 15/15; `npm run test:console` 12/12.
- Próximo passo: A1 (importar workflow no n8n) e A2 (tirar regra de negócio do canvas).
