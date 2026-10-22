import { exists, envValue, isPlaceholder, run, tryReadJson, readText } from "./repo.mjs";
import { httpProbe, tcpProbe } from "./probes.mjs";
import { serviceStatus } from "./service.mjs";

export const N8N_URL = (process.env.N8N_URL || "http://localhost:5678").replace(/\/$/, "");
export const N8N_WEBHOOK_PATH = process.env.N8N_WEBHOOK_PATH || "/webhook/intent-webhook";
export const EVOLUTION_URL = (process.env.EVOLUTION_URL || envValue("EVOLUTION_API_URL") || "http://localhost:8080").replace(/\/$/, "");

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
    howTo: ["Botão 'Iniciar serviço' no topo do Console", "ou: python intent_service.py (PORT=8001)"],
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

async function evolution() {
  const probe = await httpProbe(`${EVOLUTION_URL}/`);
  const base = {
    id: "evolution-api",
    name: "Evolution API (WhatsApp)",
    problems: ["P1", "P8"],
    phase: 1,
    howTo: [
      "Definir EVOLUTION_API_KEY no .env (chave nova, a antiga esteve no git)",
      "docker compose up -d evolution-api",
      "Criar instância e ler o QR code pelo manager da Evolution",
    ],
  };
  const details = [row("URL", EVOLUTION_URL), envRow("EVOLUTION_API_KEY")];
  if (!probe.reachable) {
    return { ...base, status: "down", summary: `Sem conexão (${probe.error})`, details };
  }
  const key = envValue("EVOLUTION_API_KEY");
  if (key && !isPlaceholder(key)) {
    const instances = await httpProbe(`${EVOLUTION_URL}/instance/fetchInstances`, { headers: { apikey: key } });
    if (instances.status === 401) {
      details.push(row("Autenticação", "EVOLUTION_API_KEY recusada (401)", "missing"));
    } else if (Array.isArray(instances.json)) {
      details.push(row("Instâncias", String(instances.json.length)));
      for (const item of instances.json.slice(0, 5)) {
        const name = item.name || item.instance?.instanceName || "instância";
        const state = item.connectionStatus || item.instance?.status || "desconhecido";
        details.push(row(name, state, state === "open" ? "ok" : "warn"));
      }
    }
  }
  return { ...base, status: "up", summary: `API respondeu HTTP ${probe.status}`, details };
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
  const [python, n8n, evo, pg, dk] = await Promise.all([pythonService(), n8nHealth(), evolution(), postgres(), docker()]);
  const webhook = await n8nWebhook(n8n.status === "up");
  return [python, n8n, webhook, evo, pg, dk, googleCalendar(), gemini()];
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
