import { h, pill, colorPill, STATUS, timeAgo } from "./dom.js";

const DECLARED = { done: "Feito", in_progress: "Em andamento", blocked: "Bloqueado", planned: "Planejado" };
const declaredColor = { done: "green", in_progress: "blue", blocked: "red", planned: "gray" };

function kpi(label, value, sub, color) {
  return h("div", { class: "card kpi" }, h("div", { class: "label" }, label), h("div", { class: "value", style: color ? `color: var(--${color})` : null }, value), h("div", { class: "muted tiny" }, sub || ""));
}

function kpis(o) {
  const t = o.tests;
  const s = o.scenarios;
  return h(
    "div",
    { class: "grid kpis" },
    kpi("Testes automatizados", t ? `${t.passed}/${t.total}` : "—", t ? (t.failed ? `${t.failed} falhando` : "todos passando") : "rode as validações", t ? (t.failed ? "red" : "green") : null),
    kpi("Cenários de conversa", s ? `${s.passed}/${s.total}` : "—", "suíte anti-alucinação", s ? (s.failed ? "red" : "green") : null),
    kpi("Checagens", `${o.counts.pass} ok`, `${o.counts.warn} avisos · ${o.counts.fail} falhas`, o.counts.fail ? "red" : o.counts.warn ? "yellow" : "green"),
    kpi("Fase atual", `Fase ${o.currentPhase}`, o.phases.find((p) => p.current)?.name),
    kpi("Última validação", o.ranAt ? timeAgo(o.ranAt) : "nunca", `status.json atualizado em ${o.updated}`),
  );
}

function roadmap(o) {
  return h(
    "div",
    { class: "grid phases" },
    o.phases.map((phase) => {
      const pct = phase.manualTotal ? Math.round((phase.manualDone / phase.manualTotal) * 100) : 100;
      return h(
        "div",
        { class: `card phase ${phase.color} ${phase.current ? "current" : ""}` },
        h("div", {}, h("small", {}, `FASE ${phase.id} · ${phase.problems.join(", ") || "governança"}`), h("h3", {}, phase.name)),
        h("div", {}, colorPill(declaredColor[phase.status], DECLARED[phase.status]), " ", phase.gateReady ? colorPill("green", "gate pronto") : null),
        h("div", { class: "muted tiny" }, `Gate: ${phase.gate}`),
        h("div", {}, h("div", { class: "muted tiny" }, `Passos manuais ${phase.manualDone}/${phase.manualTotal}`), h("div", { class: "bar" }, h("i", { style: `width:${pct}%` }))),
        h(
          "ul",
          {},
          phase.automated.map((a) => h("li", { title: a.summary }, `${STATUS[a.status]?.label || a.status}: ${a.title}`)),
        ),
        h("details", {}, h("summary", { class: "tiny muted" }, "Checklist manual"), h("ul", {}, phase.manual.map((m) => h("li", {}, `${m.done ? "☑" : "☐"} ${m.label}`)))),
      );
    }),
  );
}

const STEP_LABEL = { done: "Concluído", next: "Próximo passo", planned: "Planejado" };
const stepColor = { done: "green", next: "blue", planned: "gray" };

function steps(o) {
  return h(
    "div",
    { class: "grid phases" },
    o.steps.map((step) => {
      const pct = step.manualTotal ? Math.round((step.manualDone / step.manualTotal) * 100) : 100;
      return h(
        "div",
        { class: `card phase ${step.color} ${step.current ? "current" : ""}` },
        h("div", {}, h("small", {}, `PASSO ${step.id}`), h("h3", {}, step.name)),
        h("div", {}, colorPill(stepColor[step.status] || "gray", STEP_LABEL[step.status] || step.status), " ", step.ready ? colorPill("green", "pronto") : null),
        h("div", { class: "muted tiny" }, step.goal),
        h("div", {}, h("div", { class: "muted tiny" }, `Itens manuais ${step.manualDone}/${step.manualTotal}`), h("div", { class: "bar" }, h("i", { style: `width:${pct}%` }))),
        step.automated.length ? h("ul", {}, step.automated.map((a) => h("li", { title: a.summary }, `${STATUS[a.status]?.label || a.status}: ${a.title}`))) : null,
        h("details", {}, h("summary", { class: "tiny muted" }, "Checklist e comandos"), h("ul", {}, step.manual.map((m) => h("li", {}, `${m.done ? "☑" : "☐"} ${m.label}`))), h("ul", { class: "howto mono" }, step.how.map((c) => h("li", {}, c)))),
      );
    }),
  );
}

function problemsTable(o) {
  return h(
    "div",
    { class: "card table-wrap" },
    h(
      "table",
      {},
      h("thead", {}, h("tr", {}, ["ID", "Problema", "Fase", "Dono", "Declarado", "Evidência", "Código", "Ambiente", "Pendências"].map((c) => h("th", {}, c)))),
      h(
        "tbody",
        {},
        o.problems.map((p) => {
          const ev = p.evidence;
          const evText = [ev.tests.passed + ev.tests.failed ? `testes ${ev.tests.passed}/${ev.tests.passed + ev.tests.failed}` : null, ev.scenarios.total ? `cenários ${ev.scenarios.passed}/${ev.scenarios.total}` : null].filter(Boolean).join(" · ") || "—";
          return h(
            "tr",
            {},
            h("td", {}, h("strong", {}, p.id)),
            h("td", {}, p.title, h("div", { class: "muted tiny" }, `${p.runtime} · ${p.source}`)),
            h("td", {}, String(p.phase)),
            h("td", {}, p.owner),
            h("td", {}, colorPill(declaredColor[p.declared], DECLARED[p.declared])),
            h("td", { class: "tiny" }, evText, ev.scenarios.failing.length ? h("div", { class: "diverge" }, `falhando: ${ev.scenarios.failing.join(", ")}`) : null),
            h("td", {}, pill(p.verified), p.diverges ? h("div", { class: "diverge tiny" }, "declarado ≠ evidência") : null),
            h("td", {}, p.environment === "none" ? colorPill("gray", "n/a") : colorPill(p.environment, { green: "No ar", yellow: "Parcial", red: "Fora do ar" }[p.environment])),
            h("td", { class: "tiny" }, p.checkIssues.map((i) => h("div", {}, `${STATUS[i.status].label}: ${i.title}`)), p.envIssues.map((i) => h("div", { class: "muted" }, `Ambiente: ${i.title.replace("Integração: ", "")}`))),
          );
        }),
      ),
    ),
  );
}

function findings(o) {
  if (!o.ranAt) return h("div", { class: "card empty" }, "Rode as validações para ver os pontos de atenção.");
  if (!o.findings.length) return h("div", { class: "card empty" }, "Nenhum ponto de atenção.");
  return h(
    "div",
    { class: "grid cards-2" },
    o.findings.map((f) =>
      h(
        "div",
        { class: "card" },
        h("div", { style: "display:flex;gap:8px;align-items:center;margin-bottom:6px" }, colorPill(f.severity === "alta" ? "red" : "yellow", `Severidade ${f.severity}`), f.problems.map((p) => colorPill("gray", p))),
        h("strong", {}, f.title),
        h("div", { class: "muted tiny", style: "margin:4px 0 8px" }, f.summary),
        h("ul", { class: "howto" }, f.items.map((it) => h("li", {}, `${it.label}${it.text ? ` — ${it.text}` : ""}`))),
      ),
    ),
  );
}

function actions(o) {
  const color = { alta: "red", media: "yellow", baixa: "gray" };
  return h(
    "div",
    { class: "card table-wrap" },
    h(
      "table",
      {},
      h("thead", {}, h("tr", {}, ["#", "Prioridade", "P*", "Fase", "Dono", "Ação"].map((c) => h("th", {}, c)))),
      h("tbody", {}, o.nextActions.map((a) => h("tr", {}, h("td", {}, a.id), h("td", {}, colorPill(color[a.priority] || "gray", a.priority)), h("td", {}, a.problem), h("td", {}, String(a.phase)), h("td", {}, a.owner), h("td", {}, a.title)))),
    ),
  );
}

function raid(o) {
  if (!o.raid.length) return h("div", { class: "card empty" }, "RAID vazio.");
  const cols = Object.keys(o.raid[0]);
  return h("div", { class: "card table-wrap" }, h("table", {}, h("thead", {}, h("tr", {}, cols.map((c) => h("th", {}, c)))), h("tbody", {}, o.raid.map((r) => h("tr", {}, cols.map((c) => h("td", {}, r[c])))))));
}

function inventory(o) {
  const kindColor = { canônico: "green", orquestração: "blue", infra: "blue", legado: "yellow", experimento: "yellow", atalho: "gray", arquivo: "gray" };
  return h(
    "div",
    { class: "card table-wrap" },
    h(
      "table",
      {},
      h("thead", {}, h("tr", {}, ["Caminho", "Tipo", "Decisão", "Nota"].map((c) => h("th", {}, c)))),
      h("tbody", {}, o.inventory.map((i) => h("tr", {}, h("td", { class: "mono" }, i.path), h("td", {}, colorPill(kindColor[i.kind] || "gray", i.kind)), h("td", {}, i.decision), h("td", { class: "muted" }, i.note)))),
    ),
  );
}

function history(o) {
  if (!o.history.length) return null;
  return h(
    "div",
    { class: "card table-wrap" },
    h(
      "table",
      {},
      h("thead", {}, h("tr", {}, ["Quando", "Testes", "Cenários", "OK", "Avisos", "Falhas"].map((c) => h("th", {}, c)))),
      h(
        "tbody",
        {},
        [...o.history].reverse().slice(0, 8).map((e) => h("tr", {}, h("td", {}, new Date(e.at).toLocaleString("pt-BR")), h("td", {}, e.tests ? `${e.tests.passed}/${e.tests.total}` : "—"), h("td", {}, e.scenarios ? `${e.scenarios.passed}/${e.scenarios.total}` : "—"), h("td", {}, String(e.counts.pass)), h("td", {}, String(e.counts.warn)), h("td", {}, String(e.counts.fail)))),
      ),
    ),
  );
}

export function renderPainel(o) {
  const section = (title, body, hint) => h("div", { class: "section" }, h("h2", {}, title, hint ? h("span", { class: "muted tiny" }, hint) : null), body);
  return h(
    "div",
    {},
    kpis(o),
    section("Passo a passo da execução", steps(o), "contorno azul = passo atual · avança quando os itens manuais e as checagens ficam verdes"),
    section("Roadmap por fase", roadmap(o), "borda = evidência automática · contorno verde = fase atual"),
    section("Problemas canônicos P1–P10", problemsTable(o), "declarado (status.json) × código verificado (testes, cenários, config) × ambiente (integrações)"),
    section("Pontos de atenção", findings(o)),
    section("Próximas ações (backlog do TPM)", actions(o)),
    section("RAID", raid(o)),
    section("O que já temos (inventário e decisão)", inventory(o)),
    history(o) ? section("Histórico de validações", history(o)) : null,
  );
}
