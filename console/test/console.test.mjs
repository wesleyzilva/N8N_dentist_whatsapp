import assert from "node:assert/strict";
import http from "node:http";
import { after, before, describe, test } from "node:test";

const SERVICE_PORT = 18001 + Math.floor(Math.random() * 500);
const FAKE_N8N_PORT = 19001 + Math.floor(Math.random() * 500);
process.env.SERVICE_PORT = String(SERVICE_PORT);
process.env.N8N_URL = `http://127.0.0.1:${FAKE_N8N_PORT}`;

const { createServer } = await import("../server.mjs");
const { parseJunit } = await import("../lib/checks.mjs");
const { probeAll } = await import("../lib/integrations.mjs");
const { findPython } = await import("../lib/repo.mjs");
const { startService, stopService } = await import("../lib/service.mjs");

const python = findPython();
let base;
let consoleServer;
let fakeN8n;

const post = (path, body, headers = { "X-TPM-Console": "1" }) =>
  fetch(`${base}${path}`, { method: "POST", headers: { "Content-Type": "application/json", ...headers }, body: JSON.stringify(body) });

before(async () => {
  consoleServer = createServer();
  await new Promise((resolve) => consoleServer.listen(0, "127.0.0.1", resolve));
  base = `http://127.0.0.1:${consoleServer.address().port}`;

  fakeN8n = http.createServer((req, res) => {
    res.setHeader("Content-Type", "application/json");
    if (req.url === "/healthz") return res.end(JSON.stringify({ status: "ok" }));
    if (req.url === "/webhook/intent-webhook" && req.method === "GET") {
      res.statusCode = 404;
      return res.end(JSON.stringify({ code: 404, message: "This webhook is not registered for GET requests. Did you mean to make a POST request?" }));
    }
    res.statusCode = 404;
    res.end(JSON.stringify({ code: 404, message: "not registered" }));
  });
  await new Promise((resolve) => fakeN8n.listen(FAKE_N8N_PORT, "127.0.0.1", resolve));
});

after(async () => {
  await stopService();
  consoleServer.close();
  fakeN8n.close();
});

describe("parseJunit", () => {
  test("lê aprovados, falhas e arquivo de origem", () => {
    const xml = `<testsuite><testcase classname="tests.test_turn" name="test_ok" time="0.01"/>
      <testcase classname="tests.test_turn" name="test_bad" time="0.02"><failure message="assert &apos;a&apos; == &apos;b&apos;">trace</failure></testcase>
      <testcase classname="tests.test_grounding" name="test_skip" time="0"><skipped message="x"/></testcase></testsuite>`;
    const cases = parseJunit(xml);
    assert.deepEqual(cases.map((c) => c.outcome), ["passed", "failed", "skipped"]);
    assert.equal(cases[1].file, "tests/test_turn.py");
    assert.match(cases[1].message, /'a' == 'b'/);
  });
});

describe("segurança do console", () => {
  test("POST sem cabeçalho X-TPM-Console é recusado", async () => {
    const response = await post("/api/simulate", { message: "oi" }, {});
    assert.equal(response.status, 403);
  });

  test("Host que não é local é recusado", async () => {
    const status = await new Promise((resolve) => {
      const req = http.request({ host: "127.0.0.1", port: consoleServer.address().port, path: "/api/overview", headers: { Host: "evil.example.com" } }, (res) => {
        res.resume();
        resolve(res.statusCode);
      });
      req.end();
    });
    assert.equal(status, 403);
  });

  test("leitura de documentos não escapa do repositório", async () => {
    for (const path of ["../../etc/passwd", "package.json", "console/server.mjs"]) {
      const response = await fetch(`${base}/api/doc?path=${encodeURIComponent(path)}`);
      assert.equal(response.status, 404, path);
    }
    const ok = await fetch(`${base}/api/doc?path=${encodeURIComponent("docs/canonical/CANONICAL_MAP.md")}`);
    assert.equal(ok.status, 200);
  });
});

describe("visão do TPM", () => {
  test("overview traz P1–P10, 7 fases, backlog e inventário", async () => {
    const data = await (await fetch(`${base}/api/overview`)).json();
    assert.equal(data.problems.length, 10);
    assert.equal(data.phases.length, 7);
    assert.ok(data.nextActions.length > 0);
    assert.ok(data.inventory.length > 0);
    assert.ok(data.steps.length > 0 && data.steps.some((s) => s.current));
    assert.ok(data.raid.length > 0);
  });

  test("docs listados incluem o mapa canônico", async () => {
    const docs = await (await fetch(`${base}/api/docs`)).json();
    assert.ok(docs.some((d) => d.path === "docs/canonical/CANONICAL_MAP.md"));
  });
});

describe("integrações", () => {
  test("detecta webhook n8n ativo pela mensagem 'Did you mean POST'", async () => {
    const items = await probeAll();
    const byId = Object.fromEntries(items.map((i) => [i.id, i]));
    assert.equal(byId.n8n.status, "up");
    assert.equal(byId["n8n-webhook"].status, "up");
    assert.ok(["not_configured", "manual"].includes(byId["whatsapp-meta"].status));
    assert.equal(byId["google-calendar"].status, "not_configured");
  });

  test("nenhum valor de segredo aparece nas integrações", async () => {
    process.env.GEMINI_API_KEY = "AIzaSyDUMMYDUMMYDUMMYDUMMYDUMMYDUMMY123";
    const text = JSON.stringify(await probeAll());
    delete process.env.GEMINI_API_KEY;
    assert.ok(!text.includes("AIzaSyDUMMY"));
  });
});

describe("simulador e cenários (exigem Python)", { skip: !python }, () => {
  test("inicia o serviço com simulação e responde por modo de calendário", async () => {
    const status = await startService();
    assert.equal(status.running, true);
    assert.equal(status.simulationEnabled, true);

    const missing = await (await post("/api/simulate", { message: "Quero ver disponibilidade", number: "5546999887766", calendar_mode: "missing" })).json();
    assert.equal(missing.response.availability_evidence, "missing");
    assert.doesNotMatch(missing.response.reply_text, /\d{1,2}:\d{2}/);

    const errored = await (await post("/api/simulate", { message: "Quero ver disponibilidade", number: "5546999887766", calendar_mode: "error" })).json();
    assert.equal(errored.response.tool_status.freebusy, "error");
    assert.equal(errored.response.availability_evidence, "missing");

    const fixture = await (await post("/api/simulate", { message: "Quero ver disponibilidade", number: "5546999887766", calendar_mode: "fixture" })).json();
    assert.match(fixture.response.reply_text, /09:00/);
  });

  test("conversa multi-turno guarda unidade e reset limpa a memória curta", async () => {
    const number = "5546988776655";
    await post("/api/simulate/reset", { number });
    const first = await (await post("/api/simulate", { message: "Vou confirmar minha consulta", number })).json();
    assert.equal(first.response.session.unit_confirmed, false);
    const second = await (await post("/api/simulate", { message: "sim", number })).json();
    assert.equal(second.response.session.unit_confirmed, true);
    await post("/api/simulate/reset", { number });
    const third = await (await post("/api/simulate", { message: "Vou confirmar minha consulta", number })).json();
    assert.equal(third.response.session.hit, false);
  });

  test("suíte de cenários passa em processo e contra o serviço HTTP", async () => {
    for (const target of ["in-process", "service"]) {
      const report = await (await post("/api/scenarios/run", { target })).json();
      assert.equal(report.summary.failed, 0, `${target}: ${JSON.stringify(report.scenarios.filter((s) => s.status !== "passed").map((s) => s.id))}`);
      assert.equal(report.summary.error, 0);
      assert.ok(report.summary.total >= 15);
    }
  });

  test("checagens rápidas rodam e não vazam valores de .env", async () => {
    const run = await (await post("/api/checks/run", { ids: ["config:json", "mcp:schemas", "secrets:scan", "env:vars"] })).json();
    assert.equal(run.results["config:json"].status !== "fail", true);
    assert.equal(run.results["mcp:schemas"].status, "pass");
    assert.ok(run.results["secrets:scan"].status !== "fail", JSON.stringify(run.results["secrets:scan"].details));
  });
});
