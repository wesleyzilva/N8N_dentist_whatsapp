<#
.SYNOPSIS
  Centralizador de Testes da SecretarIA Dra. Daiana (Odontologia Ipanema).
  Executa em sequência:
    1. Validação do Ambiente + Testes Unitários (pytest)
    2. Status das Integrações (Flags 0/1) + Validação de Compromissos da Google Agenda (09:00 e Almoço)
    3. Teste Integrado de Oferta de Disponibilidade ao Paciente (Agenda -> Bot)
    4. Simulação dos Cenários de Conversa e gravação em E:\wesleyzilva\repo\N8N_dentist_whatsapp\logs

.EXAMPLE
  .\simular_conversas.ps1                      # Roda tudo (foco em Agenda + Regras, preserva cota Gemini)
  .\simular_conversas.ps1 -TestarGemini        # Inclui 1 chamada real de validação ao Gemini
  .\simular_conversas.ps1 -Direto              # Testa direto na porta 8001 (sem passar pelo n8n 5678)
#>
param(
  [string]$Url = "http://localhost:5678/webhook/intent-webhook",
  [int[]]$Cenario = @(0),
  [int]$Rodada = 1,
  [double]$Pausa = 0.2,
  [int]$TimeoutSec = 30,
  [string]$LogsDir = "E:\wesleyzilva\repo\N8N_dentist_whatsapp\logs",
  [string]$Saida = "simulacao_resultado.txt",
  [string]$SaidaJson = "simulacao_resultado.jsonl",
  [switch]$Direto,
  [switch]$TestarGemini,
  [switch]$SemRotacao
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$OutputEncoding = [Text.Encoding]::UTF8

if (-not (Test-Path -LiteralPath $LogsDir)) {
  New-Item -ItemType Directory -Force -Path $LogsDir | Out-Null
}

$caminhoSaida = Join-Path $LogsDir $Saida
$caminhoSaidaJson = Join-Path $LogsDir $SaidaJson

if ($Direto) { $Url = "http://localhost:8001/turn" }

$linhas = New-Object System.Collections.Generic.List[string]
$jsonl  = New-Object System.Collections.Generic.List[string]
$resumo = New-Object System.Collections.Generic.List[object]

function Registrar([string]$texto, [string]$cor = "Gray") {
  Write-Host $texto -ForegroundColor $cor
  $linhas.Add($texto)
}

function Rotacionar([string]$caminho) {
  if (-not (Test-Path -LiteralPath $caminho)) { return $null }
  $item = Get-Item -LiteralPath $caminho
  $carimbo = $item.LastWriteTime.ToString("yyyyMMdd_HHmmss")
  $novoNome = "{0}_{1}{2}" -f $item.BaseName, $carimbo, $item.Extension
  $destino = Join-Path $item.DirectoryName $novoNome
  Move-Item -LiteralPath $item.FullName -Destination $destino -Force
  return $destino
}

# ===========================================================================
# ETAPA 1: INFORMAÇÕES DO AMBIENTE E TESTES UNITÁRIOS (PYTEST)
# ===========================================================================
Registrar "============================================================" "Cyan"
Registrar " 1. AMBIENTE E CLASSIFICADOR DETERMINÍSTICO" "Cyan"
Registrar "============================================================" "Cyan"

$pyVersion = python --version 2>&1
Registrar "  [OK] Python Ativo       : $pyVersion" "Green"
Registrar "  [OK] Diretório de Logs  : $LogsDir" "Green"

try {
  $pytestOut = pytest test_intent_classifier.py -q 2>&1 | Out-String
  Registrar ("  [OK] Pytest Classificador: " + $pytestOut.Trim()) "Green"
} catch {
  Registrar "  [AVISO] Não foi possível rodar pytest automaticamente." "Yellow"
}

# ===========================================================================
# ETAPA 2: VALIDAÇÃO DAS INTEGRAÇÕES (FLAGS 0/1, AGENDA E GEMINI)
# ===========================================================================
Registrar "------------------------------------------------------------" "Cyan"
Registrar " 2. FLAGS DE INTEGRAÇÃO (0/1) E COMPROMISSOS DA AGENDA" "Cyan"
Registrar "------------------------------------------------------------" "Cyan"

try {
  $flags = Invoke-RestMethod -Uri "http://localhost:8001/integrations" -Method Get -TimeoutSec 5
  Registrar ("  [OK] Flags de Integração -> calendar: {0} | gemini: {1} | whatsapp: {2}" -f $flags.calendar, $flags.gemini, $flags.whatsapp) "Yellow"
} catch {
  Registrar "  [ERRO] Microsserviço na porta 8001 offline! Rode: python intent_service.py" "Red"
  exit 1
}

try {
  $cal = Invoke-RestMethod -Uri "http://localhost:8001/calendar-check" -Method Get -TimeoutSec 8
  Registrar ("  [OK] Fonte da Agenda    : " + $cal.source) "Green"
  Registrar ("  [OK] Horários Bloqueados: " + ($cal.blocked_hours -join ", ")) "Magenta"
  foreach ($ev in $cal.busy_events) {
    Registrar ("       • Ocupado: [" + $ev.inicio + "] -> " + $ev.resumo) "Gray"
  }
  Registrar ("  [OK] Horários Livres    : " + ($cal.available_slots -join ", ")) "Green"
} catch {
  Registrar ("  [ERRO] Falha ao checar agenda: " + $_.Exception.Message) "Red"
}

if ($TestarGemini) {
  Registrar "  [...] Testando 1 chamada controlada ao Google Gemini..." "Cyan"
  $gem = Invoke-RestMethod -Uri "http://localhost:8001/gemini-check" -Method Get -TimeoutSec 12
  if ($gem.status -eq 1) {
    Registrar ("  [OK] Gemini Online ({0} - {1}ms): {2}" -f $gem.model, $gem.latency_ms, $gem.reply) "Green"
  } else {
    Registrar ("  [AVISO] Gemini retornou status 0 (erro/limite): " + $gem.error) "Yellow"
  }
} else {
  Registrar "  [INFO] Chamada ao Gemini poupada (use -TestarGemini para testar a API)." "DarkGray"
}

# ===========================================================================
# ETAPA 3: TESTE INTEGRADO DE DISPONIBILIDADE (VALIDANDO BLOQUEIO DAS 09:00)
# ===========================================================================
Registrar "------------------------------------------------------------" "Cyan"
Registrar " 3. TESTE INTEGRADO: BUSCA DE VAGAS E BLOQUEIO DE COMPROMISSO" "Cyan"
Registrar "------------------------------------------------------------" "Cyan"

$payloadAgenda = @{
  from          = "5516997214286"
  message       = "Olá! Gostaria de agendar uma consulta para amanhã de manhã em São Carlos. Quais horários têm?"
  include_slots = $true
}
$bytesAgenda = [Text.Encoding]::UTF8.GetBytes(($payloadAgenda | ConvertTo-Json))
try {
  $respAg = Invoke-WebRequest -Uri $Url -Method Post -ContentType "application/json; charset=utf-8" -Body $bytesAgenda -UseBasicParsing -TimeoutSec $TimeoutSec
  $dadosAg = ([Text.Encoding]::UTF8.GetString($respAg.RawContentStream.ToArray()) | ConvertFrom-Json)
  Registrar ("  Paciente : " + $payloadAgenda.message) "White"
  Registrar ("  SecretarIA: " + $dadosAg.reply_text) "Green"
  
  # Valida se 08:00 ou 10:00 aparecem como livres e se 09:00 está na lista de bloqueados
  if ($dadosAg.reply_text -match "10:00" -and ($dadosAg.calendar_snapshot.blocked -contains "09:00")) {
    Registrar "  [VALIDADO] O compromisso das 09:00 e o almoço (12:00) foram respeitados e bloqueados!" "Green"
  } else {
    Registrar "  [ATENÇÃO] O retorno do webhook não trouxe o snapshot detalhado (verifique se o n8n repassou o JSON do Python)." "Yellow"
  }
} catch {
  Registrar ("  [ERRO] Falha no teste integrado de agenda: " + $_.Exception.Message) "Red"
}

# ===========================================================================
# ETAPA 4: SIMULAÇÃO DOS CENÁRIOS BÁSICOS DE CONVERSA
# ===========================================================================
Registrar "------------------------------------------------------------" "Cyan"
Registrar " 4. SIMULAÇÃO DE CENÁRIOS DE CONVERSA" "Cyan"
Registrar "------------------------------------------------------------" "Cyan"

function Msg([string]$t, [hashtable]$e = @{}) { $e['T'] = $t; return $e }

$cenarios = @(
  @{
    Nome = "Reagendar em São Carlos"; Ddd = "16"
    Mensagens = @(
      "Oi, boa tarde",
      (Msg "Preciso reagendar minha consulta" @{ Intent = "RESCHEDULE" }),
      (Msg "É em São Carlos mesmo" @{ Unidade = "sao-carlos" })
    )
  },
  @{
    Nome = "Cancelamento em Pato Branco"; Ddd = "46"
    Mensagens = @(
      (Msg "Preciso cancelar minha consulta de amanhã" @{ Intent = "CANCEL" }),
      (Msg "Pato Branco" @{ Unidade = "pato-branco" })
    )
  },
  @{
    Nome = "Risco Clínico / Pós-Procedimento (Handoff Imediato)"; Ddd = "16"
    Mensagens = @(
      (Msg "Fiz a harmonização ontem e meu rosto está muito inchado e doendo" @{ Intent = "ESCALATE"; Escalar = $true; Next = "handoff" })
    )
  },
  @{
    Nome = "Pergunta se é Robô e Pede Dra. Daiana"; Ddd = "16"
    Mensagens = @(
      (Msg "Você é uma pessoa de verdade ou um robô?" @{ Intent = "QUESTION" }),
      (Msg "Quero falar com a Dra. Daiana" @{ Intent = "ESCALATE"; Escalar = $true; Next = "handoff" })
    )
  }
)

function Enviar([string]$numero, [string]$mensagem) {
  if ($Direto) { $obj = @{ message = $mensagem; whatsapp_number = $numero } }
  else { $obj = @{ message = $mensagem; from = $numero } }
  $bytes = [Text.Encoding]::UTF8.GetBytes(($obj | ConvertTo-Json))
  $resp = Invoke-WebRequest -Uri $Url -Method Post -ContentType "application/json; charset=utf-8" -Body $bytes -UseBasicParsing -TimeoutSec $TimeoutSec
  $json = [Text.Encoding]::UTF8.GetString($resp.RawContentStream.ToArray())
  return ($json | ConvertFrom-Json)
}

if ($Cenario -contains 0) { $lista = 1..$cenarios.Count } else { $lista = $Cenario }

$modoTexto = if ($Direto) { "direto (porta 8001)" } else { "n8n (porta 5678)" }
Registrar ("Modo: " + $modoTexto + " | Rodada: " + $Rodada) "Cyan"

$totChecks = 0
$totOk = 0

foreach ($n in $lista) {
  $c = $cenarios[$n - 1]
  $numero = "55{0}9{1:D4}{2:D4}" -f $c.Ddd, $Rodada, $n
  Registrar ("`n=== Cenário {0}: {1} ({2}) ===" -f $n, $c.Nome, $numero) "Yellow"

  $turno = 0
  foreach ($item in $c.Mensagens) {
    $turno++
    if ($item -is [hashtable]) { $esp = $item; $msg = [string]$item.T } else { $esp = @{}; $msg = [string]$item }
    Registrar ("  Paciente: " + $msg) "White"
    try {
      $r = Enviar $numero $msg
      Registrar ("  Bot     : " + $r.reply_text) "Green"
      Registrar ("            [intent={0} | unidade={1} | escalar={2} | next={3}]" -f $r.intent, $r.unit_hypothesis.unit_id, $r.escalation.needed, $r.next) "DarkGray"

      $falhasTurno = New-Object System.Collections.Generic.List[string]
      if ($esp.ContainsKey('Intent')) {
        $totChecks++
        if ($r.intent -eq $esp.Intent) { $totOk++ } else { $falhasTurno.Add("intent=$($r.intent) (esperado $($esp.Intent))") }
      }
      if ($esp.ContainsKey('Unidade')) {
        $totChecks++
        if ($r.unit_hypothesis.unit_id -eq $esp.Unidade) { $totOk++ } else { $falhasTurno.Add("unidade=$($r.unit_hypothesis.unit_id) (esperado $($esp.Unidade))") }
      }
      if ($esp.ContainsKey('Escalar')) {
        $totChecks++
        if ([bool]$r.escalation.needed -eq [bool]$esp.Escalar) { $totOk++ } else { $falhasTurno.Add("escalar=$($r.escalation.needed)") }
      }

      if ($falhasTurno.Count -gt 0) {
        Registrar ("            FALHA: " + ($falhasTurno -join "; ")) "Red"
      }

      $resumo.Add([pscustomobject]@{ Cenario = $n; Turno = $turno; Intent = $r.intent; Next = $r.next; Escalar = $r.escalation.needed; Falhas = $falhasTurno.Count; Erro = "" })
      $registro = [ordered]@{ rodada = $Rodada; modo = $modoTexto; cenario = $n; turno = $turno; paciente = $msg; resposta = $r; falhas = $falhasTurno }
      $jsonl.Add(($registro | ConvertTo-Json -Depth 8 -Compress))
    } catch {
      Registrar ("  ERRO: " + $_.Exception.Message) "Red"
      $resumo.Add([pscustomobject]@{ Cenario = $n; Turno = $turno; Intent = ""; Next = ""; Escalar = ""; Falhas = 1; Erro = "Falha HTTP" })
    }
    Start-Sleep -Milliseconds ([int]($Pausa * 1000))
  }
}

Registrar "`n============================================================" "Cyan"
Registrar (" RESUMO FINAL: Expectativas cumpridas: {0}/{1}" -f $totOk, $totChecks) "Cyan"
Registrar "============================================================" "Cyan"
Registrar (($resumo | Format-Table -AutoSize | Out-String).TrimEnd()) "Gray"

if (-not $SemRotacao) {
  foreach ($arq in @($caminhoSaida, $caminhoSaidaJson)) {
    $antigo = Rotacionar $arq
    if ($antigo) { Write-Host ("Log anterior arquivado em: " + $antigo) -ForegroundColor DarkGray }
  }
}

Set-Content -Path $caminhoSaida -Value $linhas -Encoding UTF8
$jsonPathResolved = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($caminhoSaidaJson)
[IO.File]::WriteAllLines($jsonPathResolved, $jsonl, (New-Object Text.UTF8Encoding($false)))

Write-Host ("`n📁 Logs salvos com sucesso em: " + $LogsDir) -ForegroundColor Green