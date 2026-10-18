-- Schema inicial da clínica: agenda + comunicação via WhatsApp
-- Pode ser aplicado manualmente em um Postgres já existente (veja o README).

\connect clinica

CREATE EXTENSION IF NOT EXISTS btree_gist;

-- ---------------------------------------------------------------
-- Tipos
-- ---------------------------------------------------------------
CREATE TYPE status_agendamento AS ENUM
  ('agendado', 'confirmado', 'cancelado', 'concluido', 'faltou');

CREATE TYPE direcao_mensagem AS ENUM ('entrada', 'saida');

CREATE TYPE status_lembrete AS ENUM
  ('pendente', 'enviado', 'falhou', 'cancelado');

-- ---------------------------------------------------------------
-- Função utilitária: mantém atualizado_em sempre correto
-- ---------------------------------------------------------------
CREATE OR REPLACE FUNCTION set_atualizado_em()
RETURNS trigger AS $$
BEGIN
  NEW.atualizado_em = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ---------------------------------------------------------------
-- Pacientes
-- telefone_whatsapp: somente dígitos, com DDI+DDD (ex.: 5516999999999)
-- ---------------------------------------------------------------
CREATE TABLE pacientes (
  id                bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  nome              text        NOT NULL,
  telefone_whatsapp text        NOT NULL UNIQUE
                    CHECK (telefone_whatsapp ~ '^[0-9]{10,15}$'),
  cpf               text        UNIQUE,
  data_nascimento   date,
  email             text,
  observacoes       text,
  aceita_whatsapp   boolean     NOT NULL DEFAULT true,
  ativo             boolean     NOT NULL DEFAULT true,
  criado_em         timestamptz NOT NULL DEFAULT now(),
  atualizado_em     timestamptz NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_pacientes_atualizado_em
  BEFORE UPDATE ON pacientes
  FOR EACH ROW EXECUTE FUNCTION set_atualizado_em();

-- ---------------------------------------------------------------
-- Profissionais (dentistas)
-- ---------------------------------------------------------------
CREATE TABLE profissionais (
  id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  nome          text        NOT NULL,
  cro           text        UNIQUE,
  especialidade text,
  ativo         boolean     NOT NULL DEFAULT true,
  criado_em     timestamptz NOT NULL DEFAULT now(),
  atualizado_em timestamptz NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_profissionais_atualizado_em
  BEFORE UPDATE ON profissionais
  FOR EACH ROW EXECUTE FUNCTION set_atualizado_em();

-- ---------------------------------------------------------------
-- Procedimentos
-- ---------------------------------------------------------------
CREATE TABLE procedimentos (
  id           bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  nome         text           NOT NULL UNIQUE,
  duracao_min  integer        NOT NULL DEFAULT 30 CHECK (duracao_min > 0),
  valor_padrao numeric(10, 2) CHECK (valor_padrao >= 0),
  ativo        boolean        NOT NULL DEFAULT true
);

-- ---------------------------------------------------------------
-- Agendamentos
-- A restrição EXCLUDE impede dois atendimentos ativos sobrepostos
-- para o mesmo profissional (cancelados/faltas não bloqueiam o horário).
-- ---------------------------------------------------------------
CREATE TABLE agendamentos (
  id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  paciente_id     bigint             NOT NULL REFERENCES pacientes (id),
  profissional_id bigint             NOT NULL REFERENCES profissionais (id),
  procedimento_id bigint             REFERENCES procedimentos (id),
  inicio          timestamptz        NOT NULL,
  fim             timestamptz        NOT NULL,
  status          status_agendamento NOT NULL DEFAULT 'agendado',
  origem          text               NOT NULL DEFAULT 'whatsapp'
                  CHECK (origem IN ('whatsapp', 'manual')),
  observacoes     text,
  criado_em       timestamptz        NOT NULL DEFAULT now(),
  atualizado_em   timestamptz        NOT NULL DEFAULT now(),
  CHECK (fim > inicio),
  EXCLUDE USING gist (
    profissional_id WITH =,
    tstzrange(inicio, fim) WITH &&
  ) WHERE (status IN ('agendado', 'confirmado'))
);

CREATE INDEX idx_agendamentos_paciente ON agendamentos (paciente_id, inicio DESC);
CREATE INDEX idx_agendamentos_inicio   ON agendamentos (inicio);

CREATE TRIGGER trg_agendamentos_atualizado_em
  BEFORE UPDATE ON agendamentos
  FOR EACH ROW EXECUTE FUNCTION set_atualizado_em();

-- ---------------------------------------------------------------
-- Lembretes (o n8n varre os pendentes e envia no horário)
-- ---------------------------------------------------------------
CREATE TABLE lembretes (
  id             bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  agendamento_id bigint          NOT NULL REFERENCES agendamentos (id) ON DELETE CASCADE,
  tipo           text            NOT NULL CHECK (tipo IN ('24h', '2h')),
  enviar_em      timestamptz     NOT NULL,
  status         status_lembrete NOT NULL DEFAULT 'pendente',
  enviado_em     timestamptz,
  UNIQUE (agendamento_id, tipo)
);

CREATE INDEX idx_lembretes_pendentes ON lembretes (enviar_em)
  WHERE status = 'pendente';

-- ---------------------------------------------------------------
-- Histórico de mensagens do WhatsApp
-- ---------------------------------------------------------------
CREATE TABLE mensagens_whatsapp (
  id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  paciente_id   bigint           REFERENCES pacientes (id),
  telefone      text             NOT NULL,
  direcao       direcao_mensagem NOT NULL,
  conteudo      text,
  wa_message_id text             UNIQUE,
  criado_em     timestamptz      NOT NULL DEFAULT now()
);

CREATE INDEX idx_mensagens_telefone ON mensagens_whatsapp (telefone, criado_em DESC);
