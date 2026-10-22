import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import {
  abs,
  exists,
  findPython,
  gitFiles,
  isPlaceholder,
  loadEnvFile,
  readJson,
  readText,
  ROOT,
  runPython,
  tryReadJson,
  walkFiles,
} from "./repo.mjs";
import { probeAll } from "./integrations.mjs";

const PASS = "pass";
const WARN = "warn";
const FAIL = "fail";
const SKIP = "skip";

const detail = (label, status, text) => ({ label, status, text });

function worst(statuses) {
  if (statuses.includes(FAIL)) return FAIL;
  if (statuses.includes(WARN)) return WARN;
  if (statuses.length && statuses.every((s) => s === SKIP)) return SKIP;
  return PASS;
}

function decodeXml(text) {
  return text
    .replace(/&quot;/g, '"')
    .replace(/&apos;/g, "'")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&#10;/g, "\n")
    .replace(/&amp;/g, "&");
}

export function parseJunit(xml) {
  const cases = [];
  const re = /<testcase\s+([^>]*?)(\/>|>([\s\S]*?)<\/testcase>)/g;
  let match;
  while ((match = re.exec(xml))) {
    const attrs = {};
    for (const [, key, value] of match[1].matchAll(/(\w+)="([^"]*)"/g)) attrs[key] = decodeXml(value);
    const body = match[3] || "";
    let outcome = "passed";
    let message = "";
    const failure = body.match(/<(failure|error)\s+message="([^"]*)"/);
    if (failure) {
      outcome = failure[1] === "failure" ? "failed" : "error";
      message = decodeXml(failure[2]).split("\n")[0].slice(0, 300);
    } else if (/<skipped/.test(body)) {
      outcome = "skipped";
    }
    const classname = attrs.classname || "";
    const parts = classname.split(".");
    const file = (parts.length > 1 ? parts.slice(0, 2).join("/") : parts[0]) + ".py";
    cases.push({ name: attrs.name, file, outcome, message, time: Number(attrs.time || 0) });
  }
  return cases;
}

async function checkPytest() {
  const python = findPython();
  if (!python) return { status: FAIL, summary: "Python não encontrado", details: [detail("Instale Python 3.10+ ou defina PYTHON", FAIL, "")] };
  const junit = path.join(os.tmpdir(), `tpm-console-junit-${process.pid}.xml`);
  const result = await runPython(["-m", "pytest", "-q", `--junitxml=${junit}`], { timeout: 180_000 });
  if (/No module named pytest/.test(result.stderr + result.stdout)) {
    return {
      status: FAIL,
      summary: "pytest não instalado",
      details: [detail("Rode: pip install -r requirements-dev.txt", FAIL, "")],
    };
  }
  let cases = [];
  try {
    cases = parseJunit(fs.readFileSync(junit, "utf8"));
    fs.unlinkSync(junit);
  } catch {
    return { status: FAIL, summary: "pytest não gerou relatório", details: [detail("saída", FAIL, (result.stdout + result.stderr).slice(-800))] };
  }
  const byFile = {};
  for (const item of cases) {
    byFile[item.file] ||= { passed: 0, failed: 0, skipped: 0 };
    if (item.outcome === "passed") byFile[item.file].passed++;
    else if (item.outcome === "skipped") byFile[item.file].skipped++;
    else byFile[item.file].failed++;
  }
  const failures = cases.filter((c) => c.outcome === "failed" || c.outcome === "error");
  const passed = cases.filter((c) => c.outcome === "passed").length;
  return {
    status: failures.length ? FAIL : PASS,
    summary: `${passed} de ${cases.length} testes passaram${failures.length ? `, ${failures.length} falharam` : ""}`,
    details: [
      ...failures.map((f) => detail(`${f.file} :: ${f.name}`, FAIL, f.message)),
      ...Object.entries(byFile).map(([file, c]) => detail(file, c.failed ? FAIL : PASS, `${c.passed} ok${c.failed ? `, ${c.failed} falhas` : ""}`)),
    ],
    data: { total: cases.length, passed, failed: failures.length, byFile, failures },
  };
}

async function checkScenarios() {
  const result = await runPython(["-m", "scripts.run_scenarios", "--json"], { timeout: 60_000 });
  let report;
  try {
    report = JSON.parse(result.stdout);
  } catch {
    return { status: FAIL, summary: "Runner de cenários falhou", details: [detail("saída", FAIL, (result.stdout + result.stderr).slice(-800))] };
  }
  const s = report.summary;
  return {
    status: s.failed || s.error ? FAIL : PASS,
    summary: `${s.passed} de ${s.total} cenários de conversa passaram`,
    details: report.scenarios.map((sc) =>
      detail(`${sc.id} — ${sc.title}`, sc.status === "passed" ? PASS : sc.status === "skipped" ? SKIP : FAIL, `fase ${sc.phase} · ${sc.problems.join(", ")}`),
    ),
    data: report,
  };
}

function scenarioPhaseCheck(phase) {
  return async (ctx) => {
    const base = ctx.results.scenarios;
    if (!base?.data) return { status: SKIP, summary: "Cenários não executados", details: [] };
    const items = base.data.scenarios.filter((s) => s.phase === phase);
    if (!items.length) return { status: SKIP, summary: `Nenhum cenário marcado para a fase ${phase}`, details: [] };
    const failed = items.filter((s) => s.status !== "passed");
    return {
      status: failed.length ? FAIL : PASS,
      summary: `${items.length - failed.length} de ${items.length} cenários da fase ${phase} passaram`,
      details: items.map((s) => detail(s.id, s.status === "passed" ? PASS : FAIL, s.title)),
    };
  };
}

async function checkConfig() {
  const details = [];
  const files = fs.readdirSync(abs("config")).filter((f) => f.endsWith(".json"));
  const loaded = {};
  for (const file of files) {
    try {
      loaded[file] = readJson("config", file);
      details.push(detail(`config/${file}`, PASS, "JSON válido"));
    } catch (error) {
      details.push(detail(`config/${file}`, FAIL, `JSON inválido: ${error.message}`));
    }
  }
  const clinic = loaded["clinic.json"];
  if (clinic) {
    const dddById = Object.fromEntries((clinic.units || []).map((u) => [u.id, u.ddd]));
    const ok = dddById["pato-branco"] === "46" && dddById["sao-carlos"] === "16";
    details.push(detail("Unidades canônicas (pato-branco 46, sao-carlos 16)", ok ? PASS : FAIL, ""));
    details.push(
      detail(
        "Prática = harmonização orofacial",
        clinic.practice?.specialty === "harmonizacao-orofacial" ? PASS : FAIL,
        clinic.practice?.specialty || "ausente",
      ),
    );
    const ids = (clinic.units || []).map((u) => u.google_calendar_id);
    if (new Set(ids).size < ids.length) {
      details.push(detail("calendar_id distinto por unidade", WARN, "Pato Branco e São Carlos usam o mesmo calendar_id; sem isso a presença da dra (P4) não pode ser derivada por unidade"));
    }
    for (const unit of clinic.units || []) {
      if (/TO_BE_CONFIRMED/i.test(unit.address || "")) {
        details.push(detail(`Endereço — ${unit.city}`, WARN, "TO_BE_CONFIRMED: a secretária não deve citar endereço"));
      }
    }
  }
  const voice = loaded["voice.json"];
  if (voice) {
    const code = ["app/domains/secretary/voice.py", "app/domains/secretary/turn.py"].map((f) => readText(f)).join("\n");
    const used = new Set([...code.matchAll(/templates\[['"](\w+)['"]\]/g)].map((m) => m[1]));
    const missing = [...used].filter((key) => !(key in (voice.templates || {})));
    details.push(
      detail(
        "Templates de voz usados no código existem em voice.json",
        missing.length ? FAIL : PASS,
        missing.length ? `faltando: ${missing.join(", ")}` : `${used.size} templates`,
      ),
    );
  }
  const warns = details.filter((d) => d.status === WARN).length;
  return { status: worst(details.map((d) => d.status)), summary: `${files.length} arquivos de config válidos${warns ? `; ${warns} pendência(s) de dados (calendário, endereço)` : ""}`, details };
}

async function checkMcp() {
  const details = [];
  const catalog = tryReadJson("mcp", "catalog.json");
  if (!catalog) return { status: FAIL, summary: "mcp/catalog.json inválido", details: [] };
  for (const server of catalog.servers || []) {
    try {
      readJson(server.schema);
      details.push(detail(server.name, PASS, `${server.schema} · ${server.canonical_problems.join(", ")}`));
    } catch (error) {
      details.push(detail(server.name, FAIL, `schema ausente/ inválido (${server.schema})`));
    }
  }
  return { status: worst(details.map((d) => d.status)), summary: `${details.length} contratos MCP no catálogo`, details };
}

const BUSINESS_RULE_MARKERS = /(slot|hor[aá]rio|booking|should_create_event|targetHour|isRelativeBooking|ddd|unit_id|calend)/i;

async function checkWorkflows() {
  const details = [];
  const files = fs.readdirSync(abs("workflows")).filter((f) => f.endsWith(".json"));
  let callsTurn = false;
  for (const file of files) {
    let wf;
    try {
      wf = readJson("workflows", file);
    } catch (error) {
      details.push(detail(`workflows/${file}`, FAIL, `JSON inválido: ${error.message}`));
      continue;
    }
    const nodes = wf.nodes || [];
    const names = new Set(nodes.map((n) => n.name));
    const webhook = nodes.find((n) => n.type === "n8n-nodes-base.webhook");
    const http = nodes.filter((n) => n.type === "n8n-nodes-base.httpRequest");
    const target = http.map((n) => n.parameters?.url).filter(Boolean);
    if (file === "intent_workflow.json" && target.some((u) => /\/turn$/.test(u))) callsTurn = true;
    details.push(
      detail(
        `workflows/${file}`,
        PASS,
        `${nodes.length} nós · webhook ${webhook?.parameters?.path || "—"} · chama ${target.join(", ") || "nenhum serviço"}`,
      ),
    );
    const dangling = Object.entries(wf.connections || {}).flatMap(([from, conn]) => [
      ...(names.has(from) ? [] : [from]),
      ...Object.values(conn).flat(2).map((c) => c.node).filter((n) => !names.has(n)),
    ]);
    if (dangling.length) details.push(detail(`  conexões quebradas em ${file}`, FAIL, [...new Set(dangling)].join(", ")));

    for (const node of nodes.filter((n) => n.type === "n8n-nodes-base.code")) {
      const code = node.parameters?.jsCode || "";
      const hits = [...new Set((code.match(new RegExp(BUSINESS_RULE_MARKERS, "gi")) || []).map((h) => h.toLowerCase()))];
      if (hits.length && code.split("\n").length > 8) {
        details.push(
          detail(
            `  Code node "${node.name}" (${file})`,
            WARN,
            `${code.split("\n").length} linhas com regra de negócio no canvas (${hits.slice(0, 5).join(", ")}). Regra n8n: só orquestrar; mover para app/ (card A2).`,
          ),
        );
      }
    }
    for (const node of nodes.filter((n) => n.type === "n8n-nodes-base.googleCalendar")) {
      if (/@group\.calendar\.google\.com/.test(JSON.stringify(node.parameters?.calendar || ""))) {
        details.push(detail(`  Nó "${node.name}" (${file})`, WARN, "calendar_id fixo no canvas; deveria vir de config/clinic.json"));
      }
      if (node.parameters?.operation === "create") {
        details.push(detail(`  Nó "${node.name}" (${file})`, WARN, "cria evento no calendário (Fase 4 / P6): só liberar após CONFIRM explícito e gate da fase"));
      }
    }
    if (/Ã[\u0080-\u00BF]/.test(JSON.stringify(wf))) {
      details.push(detail(`  Codificação em ${file}`, WARN, "nomes/códigos com mojibake (UTF-8 lido como Latin-1); reexportar do n8n"));
    }
  }
  if (!callsTurn) details.push(detail("intent_workflow.json chama o serviço /turn", FAIL, "nenhum nó HTTP aponta para /turn"));
  const warns = details.filter((d) => d.status === WARN).length;
  return { status: worst(details.map((d) => d.status)), summary: `${files.length} workflows auditados (estático)${warns ? `; ${warns} desvio(s) da regra "n8n só orquestra"` : ""}`, details };
}

async function checkCompose() {
  const python = findPython();
  if (!python) return { status: SKIP, summary: "Python ausente", details: [] };
  const script = `
import json, sys
try:
    import yaml
except ImportError:
    print(json.dumps({"skip": "pyyaml não instalado (pip install -r requirements-dev.txt)"})); sys.exit(0)
out = []
for path in sys.argv[1:]:
    try:
        data = yaml.safe_load(open(path, encoding="utf-8"))
    except Exception as exc:
        out.append({"file": path, "error": str(exc)[:200]}); continue
    allowed = {"services", "volumes", "networks", "name", "configs", "secrets", "version"}
    extra = [k for k in data if k not in allowed and not str(k).startswith("x-")]
    services = data.get("services") or {}
    bad = [n for n, s in services.items() if not (s.get("image") or s.get("build"))]
    out.append({"file": path, "services": list(services), "extra": extra, "no_image": bad})
print(json.dumps(out))
`;
  const files = ["docker-compose.yml", "infra/docker/compose.target.yml"].filter((f) => exists(f));
  const result = await runPython(["-c", script, ...files]);
  let parsed;
  try {
    parsed = JSON.parse(result.stdout);
  } catch {
    return { status: WARN, summary: "Não foi possível validar YAML", details: [detail("saída", WARN, (result.stdout + result.stderr).slice(-400))] };
  }
  if (parsed.skip) return { status: SKIP, summary: parsed.skip, details: [] };
  const details = parsed.map((item) => {
    if (item.error) return detail(item.file, FAIL, `YAML inválido: ${item.error}`);
    if (item.extra.length) return detail(item.file, FAIL, `chaves fora de 'services' (indentação?): ${item.extra.join(", ")}`);
    if (item.no_image.length) return detail(item.file, FAIL, `serviços sem image/build: ${item.no_image.join(", ")}`);
    return detail(item.file, PASS, `serviços: ${item.services.join(", ")}`);
  });
  return { status: worst(details.map((d) => d.status)), summary: `${files.length} arquivos compose verificados`, details };
}

const SECRET_PATTERNS = [
  { name: "Chave de API literal (KEY=valor)", re: /\b[A-Z0-9_]*(?:API_KEY|AUTHENTICATION_API_KEY|SECRET|TOKEN|PASSWORD)\s*[=:]\s*['"]?(?!\$\{)([A-Za-z0-9/+_\-]{16,})/, level: FAIL },
  { name: "Chave Google (AIza...)", re: /AIza[0-9A-Za-z_\-]{30,}/, level: FAIL },
  { name: "Chave estilo OpenAI (sk-...)", re: /\bsk-[A-Za-z0-9]{20,}/, level: FAIL },
  { name: "Chave privada", re: /-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----/, level: FAIL },
  { name: "Valor padrão embutido em ${VAR:-valor}", re: /\$\{[A-Z0-9_]*(?:KEY|SECRET|TOKEN|PASSWORD)[A-Z0-9_]*:-([A-Za-z0-9]{16,})\}/, level: WARN },
  { name: "Segredo como padrão (VAR:-valor)", re: /(?:ENCRYPTION_KEY|_SECRET|_PASSWORD)[=:]\s*\$\{[^}]*:-([A-Za-z0-9]{16,})\}/, level: WARN },
];

async function checkSecrets() {
  const files = (await gitFiles()) || walkFiles();
  const details = [];
  for (const forbidden of [".env", "token.json", "credentials.json"]) {
    if (files.includes(forbidden)) details.push(detail(forbidden, FAIL, "arquivo de segredo versionado no git"));
  }
  const textExt = /\.(py|json|ya?ml|md|mjs|js|ps1|cmd|sql|mdc|txt|example)$|\.env/;
  for (const file of files) {
    if (!textExt.test(file) || file.startsWith("console/test/") || file === "console/lib/checks.mjs" || !exists(file)) continue;
    const stat = fs.statSync(abs(file));
    if (stat.size > 600_000) continue;
    const lines = readText(file).split(/\r?\n/);
    lines.forEach((line, idx) => {
      for (const pattern of SECRET_PATTERNS) {
        const match = line.match(pattern.re);
        if (!match) continue;
        const value = match[1] || match[0];
        if (isPlaceholder(value) || /^(true|false|null)$/i.test(value)) continue;
        details.push(detail(`${file}:${idx + 1}`, pattern.level, `${pattern.name} (valor oculto)`));
        break;
      }
    });
  }
  const fails = details.filter((d) => d.status === FAIL).length;
  return {
    status: worst(details.map((d) => d.status)),
    summary: details.length ? `${fails} segredo(s) literal(is) e ${details.length - fails} aviso(s)` : `${files.length} arquivos versionados sem segredo literal`,
    details: details.length ? details : [detail("Varredura", PASS, "sem ocorrências")],
  };
}

const ENV_REQUIRED = new Set(["EVOLUTION_API_KEY"]);
const ENV_GROUPS = [
  [/^(N8N_|DB_|WEBHOOK_URL|TZ$|PORT$)/, "n8n/serviço (tem padrão no compose)"],
  [/^(EVOLUTION_|WHATSAPP_)/, "WhatsApp"],
  [/^(GOOGLE_)/, "Fase 3 — Google Calendar"],
  [/^(OPENAI_|LLM_|GEMINI_)/, "Opcional — LLM"],
];

async function checkEnv() {
  const example = readText(".env.example");
  const names = [...example.matchAll(/^\s*([A-Z][A-Z0-9_]*)\s*=/gm)].map((m) => m[1]);
  const env = loadEnvFile();
  const details = [];
  if (!env.exists) details.push(detail(".env", WARN, "não existe; copie .env.example para .env"));
  let requiredMissing = 0;
  for (const name of names) {
    const group = (ENV_GROUPS.find(([re]) => re.test(name)) || [null, "Outras"])[1];
    const required = ENV_REQUIRED.has(name);
    const value = env.values[name] ?? process.env[name];
    const state = !value ? "ausente" : isPlaceholder(value) ? "placeholder" : "definida";
    const status = state === "definida" ? PASS : required ? WARN : SKIP;
    if (required && state !== "definida") requiredMissing++;
    details.push(detail(name, status, `${group} · ${state}`));
  }
  return {
    status: !env.exists ? WARN : requiredMissing ? WARN : PASS,
    summary: env.exists
      ? `${requiredMissing} variável(is) obrigatória(s) pendente(s); ${names.length} no .env.example`
      : ".env ausente (copie .env.example); valores nunca são exibidos",
    details,
  };
}

async function checkHygiene() {
  const files = (await gitFiles()) || [];
  const details = [];
  const pyc = files.filter((f) => /__pycache__|\.pyc$/.test(f));
  details.push(detail("Sem __pycache__/.pyc no git", pyc.length ? FAIL : PASS, pyc.length ? `${pyc.length} arquivos versionados` : "ok"));
  const gitignore = exists(".gitignore") ? readText(".gitignore") : "";
  for (const entry of [".env", "__pycache__/", "node_modules/"]) {
    details.push(detail(`.gitignore contém ${entry}`, gitignore.includes(entry) ? PASS : FAIL, ""));
  }
  const layout = tryReadJson("docs", "governance", "layout.json");
  if (!layout) {
    details.push(detail("docs/governance/layout.json", FAIL, "contrato de estrutura ausente ou inválido"));
  } else {
    const missing = layout.required.filter((p) => !exists(p));
    details.push(detail("Estrutura canônica completa", missing.length ? FAIL : PASS, missing.length ? `faltando: ${missing.join(", ")}` : `${layout.required.length} caminhos obrigatórios`));
    const back = layout.forbidden.filter((p) => exists(p));
    details.push(detail("Sem caminhos removidos (legacy, docker/, certs...)", back.length ? FAIL : PASS, back.length ? back.join(", ") : "ok"));
    const tops = new Set(files.map((f) => f.split("/")[0]));
    const extra = [...tops].filter((t) => !layout.root_allowed.includes(t));
    details.push(detail("Raiz só com itens do contrato", extra.length ? WARN : PASS, extra.length ? `fora do contrato: ${extra.join(", ")}` : "ok"));
  }
  const bad = details.filter((d) => d.status !== PASS).length;
  return { status: worst(details.map((d) => d.status)), summary: bad ? `${bad} ponto(s) de higiene a corrigir` : "Sem __pycache__ versionado, .gitignore ok, raiz limpa", details };
}

async function checkDocs() {
  const details = [];
  const map = readText("docs", "canonical", "CANONICAL_MAP.md");
  const canonicalIds = new Set([...map.matchAll(/^\|\s*(P\d+)\s*\|/gm)].map((m) => m[1]));
  const status = tryReadJson("docs", "governance", "status.json");
  if (!status) return { status: FAIL, summary: "docs/governance/status.json inválido", details: [] };
  const declared = new Set(status.problems.map((p) => p.id));
  const missing = [...canonicalIds].filter((id) => !declared.has(id));
  const extra = [...declared].filter((id) => !canonicalIds.has(id));
  details.push(
    detail(
      "status.json cobre P1–P10 do mapa canônico",
      missing.length || extra.length ? FAIL : PASS,
      missing.length || extra.length ? `faltando: ${missing.join(", ") || "—"}; sobrando: ${extra.join(", ") || "—"}` : `${canonicalIds.size} problemas`,
    ),
  );
  const sprints = fs.existsSync(abs("docs", "sprints")) ? fs.readdirSync(abs("docs", "sprints")).filter((f) => f.endsWith(".md")) : [];
  details.push(detail("Cards de sprint", sprints.length ? PASS : WARN, sprints.join(", ") || "nenhum"));
  const drift = [];
  for (const file of ["README.md", "IMPLEMENTATION_PLAN.md", "ARCHITECTURE.md", "docs/governance/NEXT_STEPS.md"]) {
    if (/ipanema/i.test(readText(file))) drift.push(file);
  }
  details.push(detail("Sem resíduos de outro produto (ex.: 'Odontologia Ipanema')", drift.length ? WARN : PASS, drift.join(", ") || "ok"));
  const bad = details.filter((d) => d.status !== PASS).length;
  return { status: worst(details.map((d) => d.status)), summary: bad ? `${bad} divergência(s) de governança` : `${canonicalIds.size} problemas canônicos cobertos; sem resíduos de outros produtos`, details };
}

function integrationCheck(integrationId) {
  return async (ctx) => {
    ctx.integrations ||= await probeAll();
    const item = ctx.integrations.find((i) => i.id === integrationId);
    if (!item) return { status: SKIP, summary: "Integração desconhecida", details: [] };
    const status = item.status === "up" ? PASS : item.status === "manual" || item.status === "info" ? WARN : FAIL;
    return {
      status,
      summary: item.summary,
      details: item.details.map((d) => detail(d.label, d.status === "ok" ? PASS : d.status === "info" ? SKIP : WARN, d.value)),
    };
  };
}

export const CHECKS = [
  { id: "pytest", title: "Testes automatizados (pytest)", group: "Testes", problems: [], run: checkPytest },
  { id: "scenarios", title: "Suíte de conversas (anti-alucinação)", group: "Testes", problems: ["P1", "P2", "P3", "P4", "P5", "P7", "P8", "P9"], run: checkScenarios },
  ...[1, 2, 3, 5, 6].map((phase) => ({
    id: `scenarios:phase${phase}`,
    title: `Cenários — gate da fase ${phase}`,
    group: "Gates",
    problems: [],
    derived: true,
    run: scenarioPhaseCheck(phase),
  })),
  { id: "config:json", title: "Configuração (clinic, guardrails, voz, sessão)", group: "Configuração", problems: ["P2", "P3", "P4"], run: checkConfig },
  { id: "mcp:schemas", title: "Contratos MCP", group: "Configuração", problems: ["P10"], run: checkMcp },
  { id: "workflows:audit", title: "Auditoria dos workflows n8n", group: "Orquestração", problems: ["P10", "P6"], run: checkWorkflows },
  { id: "compose:valid", title: "Docker Compose (YAML)", group: "Orquestração", problems: ["P10"], run: checkCompose },
  { id: "secrets:scan", title: "Segredos no repositório", group: "Segurança", problems: ["P9"], run: checkSecrets },
  { id: "env:vars", title: "Variáveis de ambiente (.env)", group: "Segurança", problems: ["P10"], run: checkEnv },
  { id: "structure:hygiene", title: "Higiene e estrutura do repositório", group: "Estrutura", problems: [], run: checkHygiene },
  { id: "docs:canonical", title: "Governança e mapa canônico", group: "Estrutura", problems: [], run: checkDocs },
  { id: "integration:python-service", title: "Integração: serviço Python /turn", group: "Integrações", problems: ["P10"], run: integrationCheck("python-service") },
  { id: "integration:n8n", title: "Integração: n8n", group: "Integrações", problems: ["P10"], run: integrationCheck("n8n") },
  { id: "integration:n8n-webhook", title: "Integração: webhook n8n", group: "Integrações", problems: ["P1", "P10"], run: integrationCheck("n8n-webhook") },
  { id: "integration:evolution-api", title: "Integração: Evolution API", group: "Integrações", problems: ["P1", "P8"], run: integrationCheck("evolution-api") },
  { id: "integration:google-calendar", title: "Integração: Google Calendar", group: "Integrações", problems: ["P4", "P5"], run: integrationCheck("google-calendar") },
];

export async function runChecks(ids) {
  const ctx = { results: {}, integrations: null };
  const selected = CHECKS.filter((check) => !ids || ids.includes(check.id) || (check.derived && ids.includes("scenarios")));
  const startedAll = Date.now();
  for (const check of selected) {
    const started = Date.now();
    let outcome;
    try {
      outcome = await check.run(ctx);
    } catch (error) {
      outcome = { status: FAIL, summary: `Erro ao executar a checagem: ${error.message}`, details: [] };
    }
    ctx.results[check.id] = {
      id: check.id,
      title: check.title,
      group: check.group,
      problems: check.problems,
      durationMs: Date.now() - started,
      ...outcome,
    };
  }
  return { ranAt: new Date().toISOString(), durationMs: Date.now() - startedAll, integrations: ctx.integrations, results: ctx.results };
}
