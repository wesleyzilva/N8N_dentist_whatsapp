# Princípios do template de projeto

## Objetivo central

Este projeto deve servir como referência de estrutura, documentação e fluxo de desenvolvimento para a visão OpenClaw: uma plataforma prática, modular e reutilizável para automação, IA e workflows low-code.

## Padrões adotados

### 1. Spec-Driven Development
- Começar pela especificação do comportamento esperado.
- Definir intenções, regras e guardrails antes da implementação completa.
- Usar testes para validar a especificação.

### 2. Arquitetura por domínios
- Separar regras de negócio, infraestrutura e interfaces.
- Manter cada camada com responsabilidade clara.
- Facilitar manutenção e evolução sem acoplar tudo em um único lugar.

### 3. Configuração centralizada
- Guardrails, prompts e regras devem ficar em arquivos de configuração externos.
- Evitar hardcode de comportamento essencial.

### 4. Low-code + código
- O n8n orquestra o fluxo.
- O código Python encapsula a lógica de negócio e classificação.
- O projeto fica mais fácil de evoluir sem perder flexibilidade.

### 5. Testes como parte da especificação
- Testar comportamento principal desde o início.
- Garantir que mudanças futuras não quebrem o fluxo esperado.

### 6. Documentação viva
- A documentação deve explicar a estrutura do projeto, o fluxo principal e os padrões adotados.
- O projeto deve ser fácil de copiar, adaptar e reutilizar.

## Estrutura recomendada para reuso

- docs/: visão geral, arquitetura, padrões e fluxo de desenvolvimento.
- app/domains/: lógica de negócio.
- app/infrastructure/: integração e configuração.
- app/interfaces/: interfaces externas.
- workflows/: automação low-code.
- tests/: validação de comportamento.
- scripts/: utilitários locais.

## Resultado esperado

Este projeto deve funcionar como um exemplo de referência para:
- a visão OpenClaw como plataforma de automação e IA,
- outros fluxos de automação,
- projetos com n8n,
- integrações com IA e WhatsApp,
- arquiteturas orientadas a domínios e spec-driven development.
