# Fluxo de validação por entrega

## 1. Definir o que será entregue
- nome da entrega;
- objetivo;
- critérios de aceitação.

## 2. Parametrizar o comportamento
- usar sempre os arquivos centrais:
  - config/guardrails.json
  - delivery_checklist.json

## 3. Validar localmente
- executar testes automatizados quando houver;
- executar o componente ou fluxo manualmente;
- confirmar se a saída atende ao esperado.

## 4. Registrar evidência
- guardar o resultado da execução;
- marcar se passou ou se precisa ajuste.

## 5. Prosseguir para a próxima entrega
- se passou, avança para a próxima parte;
- se falhou, ajusta o config ou o fluxo e repete a validação.
