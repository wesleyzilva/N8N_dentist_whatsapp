param(
    [string]$Message = "Vou confirmar minha consulta",
    [string]$ClassifierUrl = "http://127.0.0.1:8001/classify",
    [string]$HealthUrl = "http://127.0.0.1:8001/healthz",
    [string]$N8NWebhookUrl = "http://localhost:5678/webhook/intent-webhook"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

function Invoke-JsonPost {
    param(
        [string]$Url,
        [hashtable]$Payload
    )

    $body = $Payload | ConvertTo-Json -Compress
    return Invoke-RestMethod -Method Post -Uri $Url -ContentType 'application/json' -Body $body
}

Write-Host "[1/4] Verificando serviço local de classificação..." -ForegroundColor Cyan
try {
    $health = Invoke-RestMethod -Uri $HealthUrl -Method Get -TimeoutSec 5
    Write-Host "Serviço saudável: $($health.status)" -ForegroundColor Green
}
catch {
    Write-Host "Serviço não respondeu. Iniciando o servidor local..." -ForegroundColor Yellow
    Start-Process -FilePath "python" -ArgumentList "intent_service.py" -WorkingDirectory $repoRoot -WindowStyle Hidden
    Start-Sleep -Seconds 3
    $health = Invoke-RestMethod -Uri $HealthUrl -Method Get -TimeoutSec 5
    Write-Host "Serviço saudável: $($health.status)" -ForegroundColor Green
}

Write-Host "[2/4] Executando testes automáticos..." -ForegroundColor Cyan
pytest -q tests/test_classify_intent.py tests/test_guardrails_config.py

Write-Host "[3/4] Testando classificação via serviço HTTP..." -ForegroundColor Cyan
$payload = @{ message = $Message }
$classifyResult = Invoke-JsonPost -Url $ClassifierUrl -Payload $payload
$classifyResult | ConvertTo-Json -Depth 5

Write-Host "[4/4] Testando webhook do n8n..." -ForegroundColor Cyan
try {
    $webhookResult = Invoke-JsonPost -Url $N8NWebhookUrl -Payload $payload
    $webhookResult | ConvertTo-Json -Depth 5
}
catch {
    Write-Warning "Webhook do n8n não respondeu. Verifique se o workflow foi publicado e se o container está ativo."
    throw
}

Write-Host "Validação concluída." -ForegroundColor Green
