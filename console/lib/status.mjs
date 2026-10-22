import fs from "node:fs";
import path from "node:path";
import { abs, exists, readJson, readText, ROOT, walkFiles } from "./repo.mjs";

const CACHE_DIR = abs("console", ".cache");
const LAST_RUN = path.join(CACHE_DIR, "last-run.json");
const HISTORY = path.join(CACHE_DIR, "history.jsonl");

export function saveRun(run) {
  fs.mkdirSync(CACHE_DIR, { recursive: true });
  fs.writeFileSync(LAST_RUN, JSON.stringify(run));
  const counts = { pass: 0, warn: 0, fail: 0, skip: 0 };
  for (const result of Object.values(run.results)) counts[result.status] = (counts[result.status] || 0) + 1;
  const pytest = run.results.pytest?.data;
  const scenarios = run.results.scenarios?.data?.summary;
  const entry = {
    at: run.ranAt,
    counts,
    tests: pytest ? { passed: pytest.passed, total: pytest.total } : null,
    scenarios: scenarios ? { passed: scenarios.passed, total: scenarios.total } : null,
  };
  fs.appendFileSync(HISTORY, `${JSON.stringify(entry)}\n`);
}

export function loadLastRun() {
  try {
    return JSON.parse(fs.readFileSync(LAST_RUN, "utf8"));
  } catch {
    return null;
  }
}

export function loadHistory(limit = 30) {
  try {
    return fs
      .readFileSync(HISTORY, "utf8")
      .split("\n")
      .filter(Boolean)
      .slice(-limit)
      .map((line) => JSON.parse(line));
  } catch {
    return [];
  }
}

function parseTable(markdown) {
  const rows = markdown.split(/\r?\n/).filter((line) => /^\|/.test(line));
  if (rows.length < 3) return [];
  const header = rows[0].split("|").slice(1, -1).map((c) => c.trim());
  return rows.slice(2).map((row) => {
    const cells = row.split("|").slice(1, -1).map((c) => c.trim());
    return Object.fromEntries(header.map((h, i) => [h, cells[i] ?? ""]));
  });
}

export function loadRaid() {
  if (!exists("docs", "governance", "RAID.md")) return [];
  return parseTable(readText("docs", "governance", "RAID.md"));
}

function worstColor(colors) {
  if (colors.includes("red")) return "red";
  if (colors.includes("yellow")) return "yellow";
  if (colors.includes("green")) return "green";
  return "gray";
}

const checkColor = (status) => ({ pass: "green", warn: "yellow", fail: "red", skip: "gray" })[status] || "gray";

export function buildOverview(run) {
  const status = readJson("docs", "governance", "status.json");
  const results = run?.results || {};
  const pytest = results.pytest?.data;
  const scenarios = results.scenarios?.data?.scenarios || [];

  const problems = status.problems.map((problem) => {
    const files = Object.entries(status.test_map).filter(([, ids]) => ids.includes(problem.id)).map(([file]) => file);
    let testsPassed = 0;
    let testsFailed = 0;
    for (const file of files) {
      const entry = pytest?.byFile?.[file];
      if (entry) {
        testsPassed += entry.passed;
        testsFailed += entry.failed;
      }
    }
    const related = scenarios.filter((s) => s.problems.includes(problem.id));
    const scenFailed = related.filter((s) => s.status !== "passed" && s.status !== "skipped");
    const evidence = {
      tests: { passed: testsPassed, failed: testsFailed },
      scenarios: { passed: related.length - scenFailed.length, failed: scenFailed.length, total: related.length, failing: scenFailed.map((s) => s.id) },
    };
    const relatedChecks = Object.values(results).filter((r) => r.problems?.includes(problem.id) && !r.id.startsWith("scenarios"));
    const checks = relatedChecks.filter((r) => r.group !== "Integrações");
    const envChecks = relatedChecks.filter((r) => r.group === "Integrações");
    const checkIssues = checks.filter((r) => r.status === "fail" || r.status === "warn").map((r) => ({ id: r.id, title: r.title, status: r.status }));
    const envIssues = envChecks.filter((r) => r.status !== "pass").map((r) => ({ id: r.id, title: r.title, status: r.status, summary: r.summary }));
    let verified = "none";
    if (run) {
      if (testsFailed || scenFailed.length || checks.some((r) => r.status === "fail")) verified = "red";
      else if (checks.some((r) => r.status === "warn")) verified = "yellow";
      else if (testsPassed + related.length > 0) verified = "green";
    }
    let environment = "none";
    if (run && envChecks.length) {
      environment = envChecks.some((r) => r.status === "fail") ? "red" : envChecks.some((r) => r.status === "warn") ? "yellow" : "green";
    }
    const diverges = problem.declared === "done" && verified === "red";
    return { ...problem, evidence, checkIssues, envIssues, verified, environment, diverges };
  });

  const phases = status.phases.map((phase) => {
    const automated = phase.automated.map((id) => {
      const result = results[id];
      return { id, title: result?.title || id, status: result?.status || "pending", summary: result?.summary || "ainda não executado" };
    });
    const manualDone = phase.manual.filter((m) => m.done).length;
    const color = run ? worstColor(automated.map((a) => checkColor(a.status))) : "gray";
    const automatedPass = automated.length > 0 && automated.every((a) => a.status === "pass");
    return {
      ...phase,
      automated,
      manualDone,
      manualTotal: phase.manual.length,
      color,
      gateReady: automatedPass && manualDone === phase.manual.length,
      current: phase.id === status.current_phase,
    };
  });

  const steps = (status.execution_steps || []).map((step) => {
    const automated = step.checks.map((id) => {
      const result = results[id];
      return { id, title: result?.title || id, status: result?.status || "pending", summary: result?.summary || "ainda não executado" };
    });
    const manualDone = step.manual.filter((m) => m.done).length;
    return {
      ...step,
      automated,
      manualDone,
      manualTotal: step.manual.length,
      color: run && automated.length ? worstColor(automated.map((a) => checkColor(a.status))) : "gray",
      ready: automated.every((a) => a.status === "pass") && manualDone === step.manual.length,
      current: step.id === status.current_step,
    };
  });

  const findings = Object.values(results)
    .filter((r) => r.status === "fail" || r.status === "warn")
    .map((r) => ({
      id: r.id,
      severity: r.status === "fail" ? "alta" : "média",
      title: r.title,
      summary: r.summary,
      problems: r.problems,
      items: (r.details || []).filter((d) => d.status === "fail" || d.status === "warn").slice(0, 6),
    }))
    .sort((a, b) => (a.severity === b.severity ? 0 : a.severity === "alta" ? -1 : 1));

  const counts = { pass: 0, warn: 0, fail: 0, skip: 0 };
  for (const r of Object.values(results)) counts[r.status] = (counts[r.status] || 0) + 1;

  return {
    product: status.product,
    updated: status.updated,
    currentPhase: status.current_phase,
    howToRead: status.how_to_read,
    ranAt: run?.ranAt || null,
    counts,
    tests: pytest ? { passed: pytest.passed, failed: pytest.failed, total: pytest.total } : null,
    scenarios: results.scenarios?.data?.summary || null,
    phases,
    steps,
    problems,
    findings,
    nextActions: status.next_actions,
    inventory: status.inventory,
    raid: loadRaid(),
    history: loadHistory(),
  };
}

export function listDocs() {
  const roots = ["README.md", "AGENTS.md", "ARCHITECTURE.md", "IMPLEMENTATION_PLAN.md"];
  const files = walkFiles()
    .filter((f) => f.endsWith(".md") && !f.startsWith("node_modules") && !f.startsWith(".cursor"))
    .filter((f) => roots.includes(f) || f.startsWith("docs/") || /^(workflows|scripts|mcp|console|infra)\/README\.md$/.test(f));
  return files
    .map((file) => {
      const text = readText(file);
      const title = (text.match(/^#\s+(.+)$/m) || [null, file])[1];
      const area = file.startsWith("docs/") ? "Governança" : file.includes("/") ? "Subprojetos" : "Raiz";
      return { path: file, title, area };
    })
    .sort((a, b) => a.area.localeCompare(b.area) || a.path.localeCompare(b.path));
}

export function readDoc(rel) {
  const resolved = path.resolve(ROOT, rel);
  if (!resolved.startsWith(ROOT + path.sep) || !resolved.endsWith(".md")) throw new Error("caminho inválido");
  if (!listDocs().some((d) => d.path === rel)) throw new Error("documento não listado");
  return fs.readFileSync(resolved, "utf8").replace(/^\uFEFF/, "");
}
