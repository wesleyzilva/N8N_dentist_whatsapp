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
