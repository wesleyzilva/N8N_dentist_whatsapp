# N8N Dental WhatsApp Automation

A self-hosted agentic workflow for dental appointment confirmation and patient follow-up. The project combines n8n, a lightweight Python intent-classification service, and Docker to support conversational appointment handling through WhatsApp and related integrations.

## Overview

Dental clinics often face revenue loss from no-shows, missed confirmations, and slow manual follow-up. This solution automates the first layer of patient interaction by:

- sending confirmation reminders
- receiving patient replies through webhooks
- classifying intent as CONFIRM, RESCHEDULE, CANCEL, QUESTION, or UNKNOWN
- routing the interaction to the next appropriate workflow step

The design is intentionally modular so it can also serve as a reusable template for OpenClaw-style automation projects.

## Key Features

- Webhook-driven inbound message handling
- Intent classification with configurable guardrails
- Local-first development with Docker Compose
- n8n-based orchestration for low-code workflows
- Testable domain logic and validation scripts
- Clear separation between domain, infrastructure, and interface layers

## Architecture

The solution is structured around three main layers:

- Domain layer: business logic for intent classification and workflow rules
- Infrastructure layer: configuration loading, persistence, and environment handling
- Interface layer: HTTP endpoints and workflow integration points

### Main Components

- n8n: orchestration and workflow execution
- Python service: intent classification endpoint
- PostgreSQL: local persistence for n8n data
- Docker Compose: local environment startup
- Optional integrations: Google Calendar, WhatsApp providers, and LLM services

## Repository Structure

- app/domains: domain-specific business logic
- app/infrastructure: configuration and supporting infrastructure
- app/interfaces: HTTP entry points and integrations
- workflows: n8n workflow definitions
- tests: automated validation for classification and project structure
- scripts: local validation and operational helpers
- docs: project documentation and architecture references

## Prerequisites

- Docker Desktop and Docker Compose
- Python 3.10+ (for the local classifier service)
- Git
- Optional: Google Cloud project and WhatsApp provider credentials for full production integration

## Quick Start

1. Clone the repository
   ```bash
   git clone https://github.com/wesleyzilva/N8N_dentist_whatsapp.git
   cd N8N_dentist_whatsapp
   ```

2. Create the local environment file
   ```bash
   copy .env.example .env
   ```

3. Start the local stack
   ```bash
   docker compose up -d
   ```

4. Start the classifier service
   ```bash
   python intent_service.py
   ```

5. Validate locally
   ```bash
   pytest
   ```

   On Windows PowerShell, you can also run:
   ```powershell
   .\scripts\validate_local_flow.ps1
   ```

## Configuration

The project expects environment variables such as:

- N8N_BASIC_AUTH_USER / N8N_BASIC_AUTH_PASSWORD
- WEBHOOK_URL
- GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET
- OPENAI_API_KEY or another LLM provider key
- WHATSAPP_API_URL / WHATSAPP_API_TOKEN

See [.env.example](.env.example) for the reference template.

## Testing

The repository includes automated tests for:

- intent classification behavior
- guardrail configuration loading
- project structure expectations

Run them with:

```bash
pytest
```

## Roadmap

- Improve workflow branching for confirm, reschedule, cancel, and question paths
- Add stronger webhook validation and error handling
- Integrate Google Calendar updates and WhatsApp provider actions
- Expand the project into a reusable OpenClaw-style automation template

## License

This project is intended for internal and experimental use. Review credentials and secrets before production deployment.

