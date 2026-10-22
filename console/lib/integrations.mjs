import { exists, envValue, isPlaceholder, run, tryReadJson, readText } from "./repo.mjs";
import { httpProbe, tcpProbe } from "./probes.mjs";
import { serviceStatus } from "./service.mjs";

export const N8N_URL = (process.env.N8N_URL || "http://localhost:5678").replace(/\/$/, "");
export const N8N_WEBHOOK_PATH = process.env.N8N_WEBHOOK_PATH || "/webhook/intent-webhook";

const row = (label, value, status = "info") => ({ label, value, status });
const envRow = (name) => {
  const value = envValue(name);
  if (!value) return row(name, "não definida", "missing");
  if (isPlaceholder(value)) return row(name, "ainda é placeholder", "placeholder");
  return row(name, "definida (valor oculto)", "ok");
};

async function pythonService() {
  const status = await serviceStatus();
  const details = [row("URL", status.url), row("Gerenciado pelo Console", status.managed ? `sim (pid ${status.pid})` : "não")];
  if (status.running) {
    details.push(
      row("Simulação habilitada", status.simulationEnabled ? "sim" : "não — só /turn real (calendário vazio)", status.simulationEnabled ? "ok" : "warn"),
    );
    details.push(row("Modos de calendário", status.calendarModes.join(", ") || "—"));
  }
  return {
    id: "python-service",
    name: "Serviço Python /turn",
    problems: ["P1", "P2", "P10"],
    phase: 1,
    status: status.running ? "up" : "down",
    summary: status.running ? "Respondendo em /healthz" : `Fora do ar (${status.error || "sem resposta"})`,
    details,
    howTo: ["Botão 'Iniciar serviço' no topo do Console", "ou: python -m app.interfaces.http.intent_service (PORT=8001)"],
  };
}

async function n8nHealth() {
  const health = await httpProbe(`${N8N_URL}/healthz`);
  return {
    id: "n8n",
    name: "n8n (orquestrador)",
    problems: ["P10"],
    phase: 1,
    status: health.reachable && health.ok ? "up" : "down",
    summary: health.reachable ? `HTTP ${health.status} em ${health.ms} ms` : `Sem conexão (${health.error})`,
    details: [row("URL", N8N_URL), row("Versão no .env", envValue("N8N_VERSION") || "não fixada", envValue("N8N_VERSION") ? "ok" : "warn")],
    howTo: ["docker compose up -d", `Abrir ${N8N_URL} e criar o usuário owner no primeiro acesso`],
  };
}

async function n8nWebhook(n8nUp) {
  const base = {
    id: "n8n-webhook",
    name: "Webhook intent-webhook",
    problems: ["P1", "P10"],
    phase: 1,
    howTo: [
      "n8n > Workflows > Import from file > workflows/intent_workflow.json",
      "Ativar o workflow (toggle Active) e conferir o path intent-webhook",
      "Subir o serviço Python (porta 8001) antes de testar",
    ],
  };
  if (!n8nUp) {
    return { ...base, status: "down", summary: "n8n fora do ar; webhook não verificável", details: [] };
  }
  const probe = await httpProbe(`${N8N_URL}${N8N_WEBHOOK_PATH}`);
  const text = `${probe.text || ""}`;
  const registered = probe.status === 404 && /POST/i.test(text);
  return {
    ...base,
    status: registered ? "up" : "not_configured",
    summary: registered ? "Webhook ativo (aceita POST)" : "Workflow não importado/ativo no n8n",
    details: [row("URL", `${N8N_URL}${N8N_WEBHOOK_PATH}`), row("Resposta do n8n", `HTTP ${probe.status}`)],
  };
}

const META_GRAPH = "https://graph.facebook.com";
const META_API_VERSION = process.env.META_API_VERSION || envValue("META_API_VERSION") || "v21.0";

async function whatsappMeta() {
  const names = ["META_VERIFY_TOKEN", "META_APP_SECRET", "META_ACCESS_TOKEN", "META_PHONE_NUMBER_ID"];
  const ready = names.every((name) => {
    const value = envValue(name);
    return value && !isPlaceholder(value);
  });
  const details = names.map(envRow);
  const service = await serviceStatus();
  if (service.running) {
    const health = await httpProbe(`${service.url}/healthz`, { timeout: 1500 });
    const meta = health.json?.meta_webhook;
    if (meta) {
      details.push(row("Serviço: GET /meta/webhook (verificação)", meta.verify_token_configured ? "token configurado" : "sem META_VERIFY_TOKEN", meta.verify_token_configured ? "ok" : "warn"));
      details.push(row("Serviço: assinatura X-Hub-Signature-256", meta.signature_required ? "exigida" : "não exigida (só aceito em simulação)", meta.signature_required ? "ok" : "warn"));
    }
  } else {
    details.push(row("Serviço Python", "fora do ar; inicie para testar /meta/webhook", "warn"));
  }
  return {
    id: "whatsapp-meta",
    name: "WhatsApp Cloud API (Meta)",
    problems: ["P1", "P8"],
    phase: 1,
    status: ready ? "manual" : "not_configured",
    summary: ready
      ? "Credenciais definidas. 'Testar conexão' consulta o número no Graph API (não envia mensagem)."
      : "Faltam credenciais da Meta no .env. O fluxo já é testável sem elas: POST /meta/webhook com payloads de exemplo (testes e simulação).",
    details,
    action: ready ? "meta-ping" : null,
    howTo: [
      "developers.facebook.com > criar app (tipo Business) > produto WhatsApp > número de teste da Meta",
      "Copiar o Phone number ID e um token de acesso (permanente via usuário do sistema) para META_PHONE_NUMBER_ID e META_ACCESS_TOKEN",
      "Configuration > Webhook: URL pública do n8n, Verify token = META_VERIFY_TOKEN, campo 'messages' assinado",
      "App Secret (Configurações do app > Básico) em META_APP_SECRET: a assinatura de cada webhook é validada",
      "Em produção, o número precisa de Business verificado e templates aprovados para mensagens fora da janela de 24h",
    ],
  };
}

export async function metaPing() {
  const token = envValue("META_ACCESS_TOKEN");
  const phoneId = envValue("META_PHONE_NUMBER_ID");
  if (!token || isPlaceholder(token) || !phoneId || isPlaceholder(phoneId)) return { ok: false, message: "META_ACCESS_TOKEN / META_PHONE_NUMBER_ID não configurados" };
  const probe = await httpProbe(`${META_GRAPH}/${META_API_VERSION}/${encodeURIComponent(phoneId)}?fields=display_phone_number,verified_name,quality_rating`, {
    headers: { Authorization: `Bearer ${token}` },
    timeout: 8000,
  });
  if (!probe.reachable) return { ok: false, message: `Sem conexão com o Graph API (${probe.error})` };
  if (probe.status === 200 && probe.json) return { ok: true, message: `Número ${probe.json.display_phone_number || "?"} · ${probe.json.verified_name || "sem nome verificado"} · qualidade ${probe.json.quality_rating || "n/d"}` };
  if ([401, 403].includes(probe.status)) return { ok: false, message: `Token recusado (HTTP ${probe.status})` };
  return { ok: false, message: `HTTP ${probe.status}${probe.json?.error?.message ? `: ${probe.json.error.message}` : ""}` };
}

async function postgres() {
  const probe = await tcpProbe("127.0.0.1", 5432);
  return {
    id: "postgres",
    name: "PostgreSQL (n8n)",
    problems: ["P10"],
    phase: 1,
    status: probe.reachable ? "up" : "info",
    summary: probe.reachable ? "Porta 5432 aberta no host" : "Porta não publicada no host (esperado: só o n8n acessa pela rede do Docker)",
    details: [],
    howTo: ["Verificar com: docker compose ps (serviço postgres healthy)"],
  };
}

async function docker() {
  const version = await run("docker", ["version", "--format", "{{.Server.Version}}"], { timeout: 6000 });
  const missing = version.code === -1 || /not found|ENOENT/i.test(version.stderr);
  const compose = missing ? null : await run("docker", ["compose", "version", "--short"], { timeout: 6000 });
  return {
    id: "docker",
    name: "Docker / Compose",
    problems: ["P10"],
    phase: 1,
    status: missing ? "not_configured" : version.code === 0 ? "up" : "down",
    summary: missing
      ? "Docker não instalado neste computador"
      : version.code === 0
        ? `Engine ${version.stdout.trim()}`
        : "Docker instalado, mas o daemon não responde (abra o Docker Desktop)",
    details: compose && compose.code === 0 ? [row("Compose", compose.stdout.trim())] : [],
    howTo: ["Instalar Docker Desktop e iniciar o daemon"],
  };
}

function googleCalendar() {
  const clinic = tryReadJson("config", "clinic.json") || { units: [] };
  const ids = clinic.units.map((unit) => unit.google_calendar_id);
  const distinct = new Set(ids).size === ids.length && ids.every(Boolean);
  const workflowNodes = ["intent_workflow.json"].flatMap((file) => {
    try {
      return (JSON.parse(readText("workflows", file)).nodes || []).filter((n) => n.type === "n8n-nodes-base.googleCalendar");
    } catch {
      return [];
    }
  });
  const details = [
    envRow("GOOGLE_CLIENT_ID"),
    envRow("GOOGLE_CLIENT_SECRET"),
    envRow("GOOGLE_CALENDAR_PATO_BRANCO"),
    envRow("GOOGLE_CALENDAR_SAO_CARLOS"),
    row("config/clinic.json: calendário distinto por unidade", distinct ? "sim" : "não — as duas unidades usam o mesmo calendar_id", distinct ? "ok" : "warn"),
    row("Nós Google Calendar no workflow n8n", String(workflowNodes.length), workflowNodes.length ? "ok" : "warn"),
    row("Gateway Python em uso", "MissingCalendarGateway (cliente real ainda não implementado)", "warn"),
    row("credentials.json / token.json (OAuth local)", `${exists("credentials.json") ? "credentials ok" : "sem credentials"} / ${exists("token.json") ? "token ok" : "sem token"}`),
  ];
  return {
    id: "google-calendar",
    name: "Google Calendar",
    problems: ["P4", "P5", "P6"],
    phase: 3,
    status: "not_configured",
    summary: "Bloqueado até a Fase 3: sem cliente real no Python e sem calendários distintos por unidade. O n8n tem nós Google Calendar, cuja credencial OAuth só se valida dentro do n8n.",
    details,
    howTo: [
      "Google Cloud: criar OAuth client e preencher GOOGLE_CLIENT_ID/SECRET no .env",
      "n8n > Credentials > Google Calendar OAuth2 > Connect",
      "Informar um calendar_id por unidade em config/clinic.json",
      "Implementar GoogleCalendarGateway (card A5 em docs/governance/status.json)",
    ],
  };
}

function gemini() {
  const key = envValue("GEMINI_API_KEY") || envValue("GOOGLE_API_KEY");
  const configured = key && !isPlaceholder(key);
  return {
    id: "gemini",
    name: "Google Gemini (opcional)",
    problems: ["P1"],
    phase: 1,
    status: configured ? "manual" : "not_configured",
    summary: configured
      ? "Chave definida. Use 'Testar conexão' para validar (lista modelos, não gasta tokens)."
      : "Sem chave. O MVP não depende de LLM: o Python responde por templates.",
    details: [envRow("GEMINI_API_KEY")],
    action: configured ? "gemini-ping" : null,
    howTo: ["Criar chave no Google AI Studio e colocar GEMINI_API_KEY no .env"],
  };
}

export async function probeAll() {
  const [python, n8n, meta, pg, dk] = await Promise.all([pythonService(), n8nHealth(), whatsappMeta(), postgres(), docker()]);
  const webhook = await n8nWebhook(n8n.status === "up");
  return [python, n8n, webhook, meta, pg, dk, googleCalendar(), gemini()];
}

export async function geminiPing() {
  const key = envValue("GEMINI_API_KEY") || envValue("GOOGLE_API_KEY");
  if (!key || isPlaceholder(key)) return { ok: false, message: "GEMINI_API_KEY não configurada" };
  const probe = await httpProbe("https://generativelanguage.googleapis.com/v1beta/models?pageSize=1", {
    headers: { "x-goog-api-key": key },
    timeout: 8000,
  });
  if (!probe.reachable) return { ok: false, message: `Sem conexão com a API (${probe.error})` };
  if (probe.status === 200) return { ok: true, message: `Chave válida (HTTP 200 em ${probe.ms} ms)` };
  if (probe.status === 429) return { ok: false, message: "Chave reconhecida, mas cota esgotada (HTTP 429)" };
  if ([400, 401, 403].includes(probe.status)) return { ok: false, message: `Chave recusada (HTTP ${probe.status})` };
  return { ok: false, message: `HTTP ${probe.status}` };
}
