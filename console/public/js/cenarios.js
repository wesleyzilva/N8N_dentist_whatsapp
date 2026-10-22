import { api } from "./api.js";
import { colorPill, h, pill, toast } from "./dom.js";
import { replay } from "./simulador.js";

const statusPill = (status) => pill(status === "passed" ? "pass" : status === "skipped" ? "skip" : "fail", { passed: "Passou", failed: "Falhou", error: "Erro", skipped: "Pulado" }[status] || status);

export async function renderCenarios(root, { goto }) {
  let suite = sessionStorage.getItem("suite") || "conversations";
  let data = (await api.get(`/api/scenarios?suite=${suite}`)).data;
  let report = null;
  const suiteBar = h("div", { style: "display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px;align-items:center" });
  const groupsBox = h("div", {});
  const holder = h("div", {});
  const summary = h("div", { class: "muted", style: "margin: 0 0 12px" });

  async function run(target) {
    summary.textContent = "Executando…";
    const { data: result, ok } = await api.post("/api/scenarios/run", { target, suite });
    if (!ok) {
      summary.textContent = `Erro: ${result.error} ${result.detail || ""}`;
      return;
    }
    report = result;
    drawGroups();
    draw();
    toast(`${result.summary.passed}/${result.summary.total} cenários passaram (${result.target})`);
  }

  const SUITES = { conversations: "Conversas-chave (gates)", corpus: "Corpus simulado (variedade)", all: "Tudo" };

  function drawSuiteBar() {
    suiteBar.replaceChildren(
      h("span", { class: "muted tiny" }, "Suíte:"),
      ...Object.entries(SUITES).map(([key, label]) =>
        h("button", { class: `btn small ${suite === key ? "primary" : "ghost"}`, onClick: async () => {
          suite = key;
          sessionStorage.setItem("suite", key);
          data = (await api.get(`/api/scenarios?suite=${key}`)).data;
          report = null;
          summary.textContent = "";
          drawSuiteBar();
          drawGroups();
          draw();
        } }, label),
      ),
    );
  }

  function drawGroups() {
    if (!report?.groups || !Object.keys(report.groups).length) {
      groupsBox.replaceChildren();
      return;
    }
    groupsBox.replaceChildren(
      h("div", { class: "card table-wrap", style: "margin-bottom:12px" },
        h("table", {},
          h("thead", {}, h("tr", {}, ["Grupo", "Acertos", "Total"].map((c) => h("th", {}, c)))),
          h("tbody", {}, Object.entries(report.groups).map(([name, g]) => h("tr", {}, h("td", {}, name), h("td", {}, colorPill(g.passed === g.total ? "green" : "red", `${g.passed}`)), h("td", {}, String(g.total))))),
        ),
      ),
    );
  }

  function draw() {
    const byId = Object.fromEntries((report?.scenarios || []).map((s) => [s.id, s]));
    if (report) {
      const s = report.summary;
      summary.textContent = `Alvo: ${report.target} — ${s.passed} passaram, ${s.failed} falharam, ${s.error} erros, ${s.skipped} pulados de ${s.total}`;
    }
    holder.replaceChildren(
      ...data.scenarios.map((sc) => {
        const result = byId[sc.id];
        return h(
          "details",
          { class: "check", open: result && result.status !== "passed" && result.status !== "skipped" },
          h("summary", {}, result ? statusPill(result.status) : colorPill("gray", "não executado"), h("span", { class: "title" }, `${sc.id}`), h("span", { class: "sum" }, sc.title)),
          h(
            "div",
            { class: "detail-list" },
            h("div", { class: "muted tiny" }, `${sc.group ? `grupo ${sc.group} · ` : ""}Fase ${sc.phase} · ${sc.problems.join(", ")} · calendário: ${sc.calendar_mode} · paciente ${sc.number}`),
            result?.error ? h("div", { class: "banner red" }, result.error) : null,
            result?.reason ? h("div", { class: "banner yellow" }, result.reason) : null,
            (result?.turns || sc.turns).map((turn, i) => {
              const checks = turn.checks || [];
              return h(
                "div",
                { class: `scenario-turn ${result ? (turn.ok ? "ok" : "bad") : ""}` },
                h("div", {}, h("strong", {}, "Paciente: "), turn.say),
                result ? h("div", {}, h("strong", {}, "Secretária: "), turn.reply ?? "—") : h("div", { class: "muted tiny" }, `espera: ${JSON.stringify(sc.turns[i].expect)}`),
                checks.filter((c) => !c.ok).map((c) => h("div", { class: "diverge tiny" }, `✖ ${c.name}: esperado ${JSON.stringify(c.expected)} · obtido ${JSON.stringify(c.actual)}`)),
              );
            }),
            h("button", { class: "btn small ghost", onClick: async () => { await replay(sc); goto("simulador", { autoplay: true }); } }, "Reproduzir no simulador"),
          ),
        );
      }),
    );
  }

  root.append(
    h("p", { class: "muted", style: "margin-bottom:12px" }, "Mesmas suítes do pytest: conversations.json (gates anti-alucinação de PHASE_GATES.md) e corpus.json (mensagens variadas simuladas: saudações, erros de digitação, preço, mídia, injeção, fora do mapa e jornadas)."),
    suiteBar,
    h(
      "div",
      { style: "display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px" },
      h("button", { class: "btn primary", onClick: () => run("in-process") }, "Executar (em processo)"),
      h("button", { class: "btn", onClick: () => run("service") }, "Contra o serviço HTTP"),
      h("button", { class: "btn", onClick: () => run("n8n") }, "Contra o n8n (ponta a ponta)"),
    ),
    summary,
    groupsBox,
    holder,
  );
  drawSuiteBar();
  draw();
}
