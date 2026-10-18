# Mapa canônico — Secretária WhatsApp

Fonte única de verdade do produto. Qualquer backlog, sprint, agente ou MCP deve apontar para um problema desta lista. Itens fora daqui (VIPpocket, Customer Match, fidelidade) são **fora de escopo do MVP**.

## Problema que resolvemos

Atender clientes no WhatsApp como uma secretária humana do consultório de **harmonização orofacial** (não de odontologia geral): acolher, entender a cidade/unidade, olhar a agenda real da dra e só então responder. Nunca inventar horário, endereço, procedimento, preço ou onde a dra está.

## Prática (fato operacional)

| Campo | Valor |
|---|---|
| Especialidade | Harmonização orofacial |
| Não é | Consultório odontológico geral / clínica de dentista “de rotina” |
| Fonte | `config/clinic.json` → `practice` |

A secretária agenda e confirma o atendimento da dra. Não explica técnica, não indica produto (preenchedor, toxina etc.) e não dá conselho clínico.

## Unidades (fatos operacionais)

| id | Cidade | DDD | Uso do DDD |
|---|---|---|---|
| `pato-branco` | Pato Branco / PR | 46 | Hipótese de unidade do paciente; não prova onde a dra está agora |
| `sao-carlos` | São Carlos / SP | 16 | Idem |

Presença da dra e disponibilidade vêm só de ferramentas (calendário / bloco de viagem). DDD do paciente é pista, não fato clínico nem fato de agenda.

## Problemas canônicos

| ID | Problema | Dono runtime | MCP / fonte de verdade | Falha permitida |
|---|---|---|---|---|
| P1 | Atendimento humanizado no Zap | `SecretaryVoice` | `config/guardrails.json` | Tom frio, mensagem longa, jargão de bot |
| P2 | Não alucinar | `GuardrailGrounding` | MCP `guardrails` | Inventar horário, preço, endereço, procedimento, diagnóstico |
| P3 | Entender unidade (46 vs 16) | `Location` | MCP `clinic-locations` | Assumir unidade sem evidência |
| P4 | Onde a dra está agora | `Presence` | Calendário + `config/clinic.json` | Chutar cidade |
| P5 | Disponibilidade real | `Agenda` | MCP `google-calendar` | Oferecer slot sem `freebusy` |
| P6 | Confirmar / reagendar / cancelar | `Appointments` | Calendar write + n8n | Mutação sem confirmação explícita |
| P7 | Dúvida vs emergência vs clínico | `Triage` | Guardrails clínicos | Orientação médica automatizada |
| P8 | Escalar para humana | `Escalation` | WhatsApp interno / fila | Loop infinito com o paciente |
| P9 | LGPD, opt-out, auditoria | `Compliance` | logs + blacklist | Enviar sem consentimento |
| P10 | Orquestração confiável | `Orchestrator` (n8n) | MCP `n8n-ops` | Regras de negócio só no canvas n8n |

## Contrato de resposta (obrigatório)

Toda resposta ao paciente precisa declarar internamente:

1. `intent` classificada
2. `unit_hypothesis` (ddd / texto / unknown)
3. `presence_evidence` (tool result ou `missing`)
4. `availability_evidence` (tool result ou `missing`)
5. `allowed_claims` (o que pode ser dito)
6. `escalation` (sim/não e motivo)

Se evidência de P4 ou P5 estiver `missing`, a voz só pode: perguntar, oferecer esperar, ou escalar. Nunca preencher o vazio com modelo.

## Fora de escopo (não misturar)

- Programa de fidelidade, QR, VIPpocket, Google Ads Customer Match
- Marketing de reativação em massa no MVP
- Triagem clínica profunda / diagnóstico
