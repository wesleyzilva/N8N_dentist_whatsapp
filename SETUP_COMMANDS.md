# Setup e Execução via Linha de Comando

Este documento registra os caminhos e comandos principais para iniciar o projeto de hiperautomação. Use-o como referência nas próximas execuções.

## Posição do projeto
- Diretório base do projeto: `E:\wesleyzilva\repo\N8N_dentist_whatsapp`
- Repositório GitHub: `https://github.com/wesleyzilva/N8N_dentist_whatsapp.git`

## Arquivos importantes
- `README.md` — documentação técnica do projeto.
- `ARCHITECTURE.md` — arquitetura unificada e modelo de dados.
- `docker-compose.yml` — definição de serviços Docker.
- `.env.example` — template de variáveis de ambiente.
- `.env` — arquivo de ambiente de execução local (deve ser criado a partir do `.env.example`).

## Docker local
- Contexto Docker preferido: `desktop-linux`
- Contexto padrão disponível: `default`
- Endpoint do Docker Desktop: `npipe:////./pipe/dockerDesktopLinuxEngine`
- Endpoint do contexto padrão: `npipe:////./pipe/docker_engine`

## Comandos iniciais

### 1. Navegar para o diretório do projeto
```powershell
cd /d E:\wesleyzilva\repo\N8N_dentist_whatsapp
```

### 2. Criar arquivo de ambiente local
```powershell
copy .env.example .env
```

### 3. Atualizar variáveis no `.env`
Edite o arquivo com os valores reais antes de iniciar o ambiente.

### 4. Iniciar o Docker Compose
```powershell
docker compose up -d
```

### 5. Verificar se os containers estão rodando
```powershell
docker compose ps
```

### 6. Parar o ambiente
```powershell
docker compose down
```

## Verificação do Docker

### Verificar versão do Docker e Docker Compose
```powershell
docker --version
docker compose version
git --version
```

### Verificar se o daemon Docker está ativo
```powershell
docker info
```

Se o daemon não estiver ativo, abra o Docker Desktop.

## Requisitos adicionais no Windows

### WSL 2 e Docker Desktop
Docker Desktop para Windows normalmente depende do WSL 2. Se o Docker não iniciar e `docker info` falhar com `failed to connect to the docker API at npipe:////./pipe/docker_engine`, o WSL pode estar ausente ou não estar configurado.

### Verificar WSL
```powershell
wsl --status
wsl -l -v
```

### Instalar WSL 2 (se necessário)
```powershell
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
Restart-Computer
```

Após reiniciar:
```powershell
wsl --set-default-version 2
wsl --install -d Ubuntu
```

### Observação
Se `wsl --version` não for suportado, você está usando uma versão legada do WSL. Atualize o Windows e o WSL antes de usar o Docker Desktop.

## Configurações recomendadas

- `N8N_BASIC_AUTH_USER` — usuário de administração do n8n.
- `N8N_BASIC_AUTH_PASSWORD` — senha de administração do n8n.
- `WEBHOOK_URL` — URL pública para webhooks de WhatsApp.
- `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` — credenciais Google OAuth2.
- `OPENAI_API_KEY` — chave para LLM.
- `WHATSAPP_API_URL` / `WHATSAPP_API_TOKEN` — credenciais do provedor de WhatsApp.

## Observações

- O `.env` não deve ser versionado em repositórios públicos se contiver segredos.
- Use `docker compose up -d` somente depois de confirmar que o Docker Desktop está rodando.
- Se houver erros de daemon, verifique o Docker Desktop ou reinstale-o.

---

Arquivo criado para manter o processo de inicialização e paths registrado de forma clara.