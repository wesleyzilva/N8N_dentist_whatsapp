# Gates de fase

QA não aprova “workflow green” se grounding falhar.

## Checklist comum

- [ ] Card aponta um ID P* do mapa canônico
- [ ] Evidência de teste no repo (`tests/` ou script documentado)
- [ ] Nenhuma claim de agenda/presença sem fixture de calendário
- [ ] RAID atualizado se risco novo
- [ ] Secrets fora do git

## Gates por fase

| Fase | Gate |
|---|---|
| 0 | TPM abre sprint P* sem consultar docs órfãos (VIPpocket) |
| 1 | Round-trip webhook → intent → texto humanizado local |
| 2 | Casos 46, 16, DDD outro, texto vs DDD conflitantes |
| 3 | Freebusy mock: slots reais vs calendário down |
| 4 | Mutação só após confirmação explícita; rollback documentado |
| 5 | Emergência/dor escala; sem conselho clínico |
| 6 | Opt-out, auditoria de decisão, backup de n8n |

## Evidência mínima de anti-alucinação

Três testes sempre:

1. Calendário indisponível → não sugere horário
2. Presença sem evento → não afirma cidade da dra
3. Paciente pede “qualquer horário amanhã” → lista só slots do tool
