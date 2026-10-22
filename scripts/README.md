# Scripts

Só o runner da suíte de conversas. Validação completa do projeto: `npm run validate` (TPM Console).

```bash
python -m scripts.run_scenarios                 # em processo
python -m scripts.run_scenarios --json          # saída completa (usada pelo TPM Console)
python -m scripts.run_scenarios --only S05 S09  # por prefixo de id
python -m scripts.run_scenarios --url http://localhost:8001/simulate/turn   # via HTTP (serviço com SIMULATION_ENABLED=1)
python -m scripts.run_scenarios --url http://localhost:5678/webhook/intent-webhook  # ponta a ponta no n8n
```

Os cenários ficam em `tests/scenarios/conversations.json`. O pytest roda os mesmos casos (`tests/test_scenarios.py`).
