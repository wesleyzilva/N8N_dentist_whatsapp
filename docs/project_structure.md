# Estrutura de pastas recomendada

## Objetivo

Organizar o projeto por domínio de negócio, infraestrutura e interfaces para manter o fluxo low-code simples, escalável e fácil de manter.

## Estrutura

```text
app/
  domains/
    appointments/
      intent_classifier.py
  infrastructure/
    config/
      config_loader.py
  interfaces/
    http/
      intent_service.py
config/
  guardrails.json
scripts/
  validate_local_flow.ps1
  classify_intent.py
tests/
  test_classify_intent.py
  test_guardrails_config.py
workflows/
  intent_workflow.json
```

## Como usar

- Coloque regras de negócio em app/domains.
- Coloque integrações e acesso a dados em app/infrastructure.
- Coloque entradas/saídas externos em app/interfaces.
- Use workflows no n8n como orquestração, não como repositório de regras.
- Mantenha arquivos de configuração e JSON em config/.
