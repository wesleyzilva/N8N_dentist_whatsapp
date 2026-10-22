#!/usr/bin/env node
import fs from "node:fs";
import http from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { CHECKS, runChecks } from "./lib/checks.mjs";
import { geminiPing, metaPing, N8N_URL, N8N_WEBHOOK_PATH, probeAll } from "./lib/integrations.mjs";
import { httpProbe } from "./lib/probes.mjs";
import { findPython, readJson, runPython } from "./lib/repo.mjs";
import { SERVICE_URL, serviceStatus, startService, stopService } from "./lib/service.mjs";
import { clearTurnLog, readTurnLog } from "./lib/turnlog.mjs";
import { buildOverview, listDocs, loadLastRun, readDoc, saveRun } from "./lib/status.mjs";

const PUBLIC_DIR = path.join(path.dirname(fileURLToPath(import.meta.url)), "public");
const CONSOLE_PORT = Number(process.env.CONSOLE_PORT || 4173);
const MIME = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".svg": "image/svg+xml",
};

let checkLock = Promise.resolve();
const serialized = (task) => {
  const next = checkLock.then(task, task);
  checkLock = next.catch(() => {});
  return next;
};

async function executeChecks(ids) {
  const run = await serialized(() => runChecks(ids));
  if (!ids) saveRun(run);
  return run;
}

function sendJson(res, status, body) {
  const data = JSON.stringify(body);
  res.writeHead(status, { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store" });
  res.end(data);
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    let raw = "";
    req.on("data", (chunk) => {
      raw += chunk;
      if (raw.length > 1_000_000) reject(new Error("corpo grande demais"));
    });
    req.on("end", () => {
      try {
        resolve(raw ? JSON.parse(raw) : {});
      } catch {
        reject(new Error("JSON inválido"));
      }
    });
  });
}

const LOCAL_HOST = /^(localhost|127\.0\.0\.1|\[::1\])(:\d+)?$/;

async function simulate(body) {
  const message = String(body.message ?? "");
  const number = String(body.number ?? "5546999887766");
  const target = body.target === "n8n" ? "n8n" : "python";
  const started = Date.now();

  if (target === "n8n") {
    const url = `${N8N_URL}${N8N_WEBHOOK_PATH}`;
    const probe = await httpProbe(url, { method: "POST", body: { message, from: number, name: "Paciente (simulação)" }, timeout: 20_000 });
    if (!probe.reachable) return { status: 502, body: { error: `n8n inacessível (${probe.error})`, hint: "Suba o stack e ative o workflow (aba Integrações)." } };
    return { status: 200, body: { target, endpoint: url, httpStatus: probe.status, ms: probe.ms, response: probe.json ?? { raw: probe.text } } };
  }

  const service = await serviceStatus();
  if (!service.running) return { status: 503, body: { error: "Serviço Python fora do ar", hint: "Use 'Iniciar serviço' no topo." } };
  const mode = body.calendar_mode || "missing";
  if (mode !== "missing" && !service.simulationEnabled) {
    return {
      status: 409,
      body: { error: "O serviço em execução não aceita modos de calendário de simulação", hint: "Pare-o e use 'Iniciar serviço' (inicia com SIMULATION_ENABLED=1)." },
    };
  }
  const endpoint = service.simulationEnabled ? "/simulate/turn" : "/turn";
  const probe = await httpProbe(`${SERVICE_URL}${endpoint}`, {
    method: "POST",
    body: { message, whatsapp_number: number, calendar_mode: mode, fixture_city: body.fixture_city || undefined },
    timeout: 10_000,
  });
  if (!probe.reachable || !probe.json) return { status: 502, body: { error: "Resposta inválida do serviço", detail: probe.text || probe.error } };
  return { status: probe.status, body: { target, endpoint, httpStatus: probe.status, ms: Date.now() - started, response: probe.json } };
}

async function resetSession(body) {
  const service = await serviceStatus();
  if (!service.running || !service.simulationEnabled) return { status: 200, body: { reset: false, note: "serviço sem simulação; nada a limpar" } };
  const probe = await httpProbe(`${SERVICE_URL}/simulate/reset`, { method: "POST", body: { whatsapp_number: String(body.number || "") } });
  return { status: 200, body: { reset: probe.ok } };
}

async function runScenarios(body) {
  const args = ["-m", "scripts.run_scenarios", "--json"];
  if (["corpus", "all"].includes(body.suite)) args.push("--suite", body.suite);
  if (body.target === "service") args.push("--url", `${SERVICE_URL}/simulate/turn`);
  if (body.target === "n8n") args.push("--url", `${N8N_URL}${N8N_WEBHOOK_PATH}`);
  if (Array.isArray(body.only) && body.only.length) args.push("--only", ...body.only.map(String));
  const result = await runPython(args, { timeout: 120_000 });
  try {
    return { status: 200, body: JSON.parse(result.stdout) };
  } catch {
    return { status: 500, body: { error: "Runner falhou", detail: (result.stdout + result.stderr).slice(-800) } };
  }
}

async function handleApi(req, res, url) {
  const route = `${req.method} ${url.pathname}`;
  if (req.method === "POST" && req.headers["x-tpm-console"] !== "1") {
    return sendJson(res, 403, { error: "cabeçalho X-TPM-Console ausente" });
  }
  const body = req.method === "POST" ? await readBody(req) : {};

  switch (route) {
    case "GET /api/overview": {
      return sendJson(res, 200, { ...buildOverview(loadLastRun()), python: findPython(), checks: CHECKS.map(({ id, title, group }) => ({ id, title, group })) });
    }
    case "POST /api/checks/run": {
      const run = await executeChecks(Array.isArray(body.ids) && body.ids.length ? body.ids : undefined);
      return sendJson(res, 200, run);
    }
    case "GET /api/checks/last":
      return sendJson(res, 200, loadLastRun() || { results: {} });
    case "GET /api/integrations":
      return sendJson(res, 200, await probeAll());
    case "POST /api/integrations/gemini-ping":
      return sendJson(res, 200, await geminiPing());
    case "POST /api/integrations/meta-ping":
      return sendJson(res, 200, await metaPing());
    case "GET /api/service":
      return sendJson(res, 200, await serviceStatus());
    case "POST /api/service/start":
      return sendJson(res, 200, await startService());
    case "POST /api/service/stop":
      return sendJson(res, 200, await stopService());
    case "POST /api/simulate": {
      const result = await simulate(body);
      return sendJson(res, result.status, result.body);
    }
    case "POST /api/simulate/reset": {
      const result = await resetSession(body);
      return sendJson(res, result.status, result.body);
    }
    case "GET /api/scenarios": {
      const suite = url.searchParams.get("suite") || "conversations";
      const result = await serialized(() => runPython(["-m", "scripts.run_scenarios", "--list", "--suite", suite], { timeout: 30_000 }));
      try {
        return sendJson(res, 200, JSON.parse(result.stdout));
      } catch {
        return sendJson(res, 500, { error: "Não foi possível listar os cenários", detail: (result.stdout + result.stderr).slice(-400) });
      }
    }
    case "GET /api/logs":
      return sendJson(res, 200, readTurnLog(Number(url.searchParams.get("limit")) || 100));
    case "POST /api/logs/clear":
      return sendJson(res, 200, clearTurnLog());
    case "POST /api/scenarios/run": {
      const result = await serialized(() => runScenarios(body));
      return sendJson(res, result.status, result.body);
    }
    case "GET /api/docs":
      return sendJson(res, 200, listDocs());
    case "GET /api/doc": {
      try {
        return sendJson(res, 200, { path: url.searchParams.get("path"), markdown: readDoc(url.searchParams.get("path") || "") });
      } catch (error) {
        return sendJson(res, 404, { error: error.message });
      }
    }
    default:
      return sendJson(res, 404, { error: "rota não encontrada" });
  }
}

function serveStatic(req, res, url) {
  const rel = url.pathname === "/" ? "index.html" : url.pathname.slice(1);
  const file = path.resolve(PUBLIC_DIR, rel);
  if (!file.startsWith(PUBLIC_DIR + path.sep) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) {
    res.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
    res.end("não encontrado");
    return;
  }
  res.writeHead(200, { "Content-Type": MIME[path.extname(file)] || "application/octet-stream", "Cache-Control": "no-store" });
  fs.createReadStream(file).pipe(res);
}

export function createServer() {
  return http.createServer(async (req, res) => {
    if (!LOCAL_HOST.test(req.headers.host || "")) {
      res.writeHead(403);
      res.end("host não permitido");
      return;
    }
    const url = new URL(req.url, "http://localhost");
    try {
      if (url.pathname.startsWith("/api/")) await handleApi(req, res, url);
      else serveStatic(req, res, url);
    } catch (error) {
      sendJson(res, 500, { error: error.message });
    }
  });
}

const STATUS_LABEL = { pass: "OK   ", warn: "AVISO", fail: "FALHA", skip: "PULOU" };

async function cli() {
  const asJson = process.argv.includes("--json");
  const run = await executeChecks();
  if (asJson) {
    console.log(JSON.stringify(run, null, 2));
  } else {
    console.log("TPM Console — validação completa\n");
    for (const result of Object.values(run.results)) {
      console.log(`[${STATUS_LABEL[result.status]}] ${result.title}\n        ${result.summary}`);
    }
    const counts = Object.values(run.results).reduce((acc, r) => ({ ...acc, [r.status]: (acc[r.status] || 0) + 1 }), {});
    console.log(`\n${JSON.stringify(counts)} em ${(run.durationMs / 1000).toFixed(1)}s`);
    console.log("Detalhes e histórico: npm run console  →  http://localhost:" + CONSOLE_PORT);
  }
  const strict = process.argv.includes("--strict");
  const blocking = Object.values(run.results).filter((r) => r.status === "fail" && (strict || r.group !== "Integrações"));
  process.exitCode = blocking.length ? 1 : 0;
}

async function main() {
  if (process.argv.includes("--check")) return cli();
  const server = createServer();
  server.listen(CONSOLE_PORT, "127.0.0.1", async () => {
    console.log(`TPM Console em http://localhost:${CONSOLE_PORT}`);
    if (!process.argv.includes("--no-service")) {
      try {
        const status = await startService();
        console.log(status.running ? `Serviço Python /turn em ${status.url} (simulação ${status.simulationEnabled ? "ligada" : "desligada"})` : "Serviço Python não iniciou; veja a aba Integrações");
      } catch (error) {
        console.log(`Serviço Python não iniciou: ${error.message}`);
      }
    }
  });
  server.on("error", (error) => {
    console.error(error.code === "EADDRINUSE" ? `Porta ${CONSOLE_PORT} em uso. Use CONSOLE_PORT=4174 npm run console` : error.message);
    process.exit(1);
  });
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main();
}
