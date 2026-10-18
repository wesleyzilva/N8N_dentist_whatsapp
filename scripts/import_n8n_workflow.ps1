param(
    [string]$WorkflowFile = "intent_workflow.json"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$container = docker compose ps -q n8n
if (-not $container) {
    throw "Container n8n não está no ar. Rode: docker compose up -d"
}

Write-Host "Importando /workflows/$WorkflowFile no n8n..." -ForegroundColor Cyan
docker compose exec -T n8n n8n import:workflow --input="/workflows/$WorkflowFile" --projectId=eqLFJhy2q3uyLDDO --activeState=fromJson

Write-Host "Publicando workflow j9ZLd2huqjyrghXf..." -ForegroundColor Cyan
docker compose exec -T n8n n8n update:workflow --id=XNTMmT56aUElo2ng --active=false
docker compose exec -T n8n n8n publish:workflow --id=j9ZLd2huqjyrghXf

Write-Host "Reiniciando n8n para o webhook valer..." -ForegroundColor Cyan
docker compose restart n8n

Write-Host "Workflows no container:" -ForegroundColor Cyan
docker compose exec -T n8n n8n list:workflow
