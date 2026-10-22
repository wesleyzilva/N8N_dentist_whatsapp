-- Secretária WhatsApp: Fase 1 (canal e voz): estado mínimo da conversa
--
-- Banco separado do banco interno do n8n ("n8n"). Pode ser reaplicado sem erro.
-- O que NÃO fica aqui de propósito:
--   * agenda e presença da dra: a fonte é o Google Calendar (Fases 3 e 4)
--   * opt-out, auditoria de decisão e handoff: Fases 5 e 6
--
-- Aplicar (na raiz do repositório, com o compose rodando):
--   docker compose exec -T postgres psql -U n8n -d postgres < infra/db/migrations/001_secretaria_fase1.sql
--
-- No n8n, crie a credencial Postgres com: host = postgres, porta 5432,
-- database = secretaria, usuário/senha do seu compose.

SELECT 'CREATE DATABASE secretaria'
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'secretaria')
\gexec

\connect secretaria

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS trigger AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Uma linha por paciente (número no formato do /turn: só dígitos, DDI+DDD, ex.: 5546...)
-- unit_hypothesis: id da unidade em config/clinic.json. É hipótese de unidade do
-- paciente, nunca "onde a dra está".
-- last_inbound_at: base para a janela de 24h do WhatsApp.
CREATE TABLE IF NOT EXISTS conversation_state (
  whatsapp_number  text PRIMARY KEY
                   CHECK (whatsapp_number ~ '^[0-9]{10,15}$'),
  last_intent      text
                   CHECK (last_intent IN ('CONFIRM', 'RESCHEDULE', 'CANCEL',
                                          'QUESTION', 'AVAILABILITY', 'LOCATION', 'UNKNOWN')),
  unit_hypothesis  text,
  last_inbound_at  timestamptz,
  last_outbound_at timestamptz,
  created_at       timestamptz NOT NULL DEFAULT now(),
  updated_at       timestamptz NOT NULL DEFAULT now()
);

DROP TRIGGER IF EXISTS trg_conversation_state_updated_at ON conversation_state;
CREATE TRIGGER trg_conversation_state_updated_at
  BEFORE UPDATE ON conversation_state
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Deduplicação de webhooks reenviados pelo provedor (sem guardar o texto da mensagem,
-- por mínimo de dado/LGPD). No n8n:
--   INSERT INTO processed_messages (provider_message_id, whatsapp_number)
--   VALUES ($1, $2) ON CONFLICT DO NOTHING RETURNING 1;
-- Nenhuma linha retornada = reentrega, o workflow deve parar aqui.
CREATE TABLE IF NOT EXISTS processed_messages (
  provider_message_id text PRIMARY KEY,
  whatsapp_number     text        NOT NULL,
  received_at         timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_processed_messages_received_at
  ON processed_messages (received_at);
