# Scripts utilitários

## Validação local completa

Use o script abaixo para validar o fluxo inteiro em uma única execução:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\validate_local_flow.ps1
```

Ele executa, nesta ordem:
1. Verifica se o serviço de classificação local está no ar.
2. Executa os testes automáticos.
3. Envia uma mensagem para o serviço HTTP de classificação.
4. Envia a mesma mensagem ao webhook do n8n.

## Exemplo com mensagem customizada

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\validate_local_flow.ps1 -Message "Preciso reagendar para outro dia"
```

## Suíte de conversas

```bash
python -m scripts.run_scenarios                 # em processo
python -m scripts.run_scenarios --json          # saída completa (usada pelo TPM Console)
python -m scripts.run_scenarios --only S05 S09  # por prefixo de id
python -m scripts.run_scenarios --url http://localhost:8001/simulate/turn   # via HTTP (serviço com SIMULATION_ENABLED=1)
python -m scripts.run_scenarios --url http://localhost:5678/webhook/intent-webhook  # ponta a ponta no n8n
```

Os cenários ficam em `tests/scenarios/conversations.json`. O pytest roda os mesmos casos (`tests/test_scenarios.py`).

