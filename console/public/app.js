import { api, refreshOverview, refreshService, state } from "./js/api.js";
import { renderCenarios } from "./js/cenarios.js";
import { renderDocs } from "./js/docs.js";
import { h, pill, timeAgo, toast } from "./js/dom.js";
import { renderIntegracoes } from "./js/integracoes.js";
import { renderPainel } from "./js/painel.js";
import { renderSimulador, sim } from "./js/simulador.js";
import { renderValidacao } from "./js/validacao.js";

const VIEWS = {
  painel: ["Painel do TPM", "Fases, problemas P1–P10, evidência automática e próximas ações."],
  simulador: ["Simulador de conversa", "Converse como o paciente e veja o contrato (intent, unidade, evidências, claims, escalonamento)."],
  cenarios: ["Cenários de teste", "Suíte de conversas com expectativas de grounding; roda em processo, no HTTP ou no n8n."],
  validacao: ["Validações", "Testes, configuração, workflows, segredos, estrutura e integrações."],
  integracoes: ["Integrações", "Probes locais: serviço Python, n8n, webhook, Evolution API, Docker, Google, Gemini."],
  docs: ["Documentos", "Mapa canônico, plano, governança e READMEs do repositório."],
};

const root = document.getElementById("view");
let current = "painel";
let rendering = 0;

function goto(view, options = {}) {
  location.hash = view;
  if (options.autoplay) sessionStorage.setItem("autoplay", "1");
}

async function render() {
  const view = (location.hash.slice(1) || "painel").split("?")[0];
  current = VIEWS[view] ? view : "painel";
  const ticket = ++rendering;
  document.querySelectorAll("#nav a").forEach((a) => a.classList.toggle("active", a.dataset.view === current));
  document.getElementById("view-title").textContent = VIEWS[current][0];
  document.getElementById("view-sub").textContent = VIEWS[current][1];
  root.replaceChildren(h("div", { class: "card empty" }, "Carregando…"));
  const container = h("div", {});
  const ctx = { goto, onRan: updateRunLabel };
  switch (current) {
    case "painel": {
      const overview = await refreshOverview();
      if (!overview.ranAt && !render.autoRan) {
        render.autoRan = true;
        await runAll(true);
        return;
      }
      container.append(renderPainel(overview));
      break;
    }
    case "simulador":
      await renderSimulador(container);
      if (sessionStorage.getItem("autoplay") && sim.pending?.length) {
        sessionStorage.removeItem("autoplay");
        const steps = sim.pending;
        sim.pending = null;
        for (const text of steps) await window.__simSend(text);
      }
      break;
    case "cenarios":
      await renderCenarios(container, ctx);
      break;
    case "validacao":
      await renderValidacao(container, ctx);
      break;
    case "integracoes":
      await renderIntegracoes(container);
      break;
    case "docs":
      await renderDocs(container);
      break;
  }
  if (ticket === rendering) root.replaceChildren(container);
}

function updateRunLabel(iso) {
  document.getElementById("last-run").textContent = iso ? `Última validação ${timeAgo(iso)}` : "Validações ainda não executadas";
}

async function runAll(silent) {
  const button = document.getElementById("run-all");
  button.disabled = true;
  button.textContent = "Validando…";
  try {
    const { data } = await api.post("/api/checks/run", {});
    updateRunLabel(data.ranAt);
    if (!silent) toast("Validações concluídas");
    await refreshService();
    drawService();
    await render();
  } finally {
    button.disabled = false;
    button.textContent = "Rodar todas as validações";
  }
}

function drawService() {
  const s = state.service;
  const el = document.getElementById("service-pill");
  el.replaceChildren(pill(s?.running ? "pass" : "fail", s?.running ? `Python /turn no ar${s.simulationEnabled ? " · simulação" : ""}` : "Python /turn parado"));
  document.getElementById("service-start").disabled = Boolean(s?.running);
  document.getElementById("service-stop").disabled = !s?.managed;
}

document.getElementById("run-all").addEventListener("click", () => runAll(false));
document.getElementById("service-start").addEventListener("click", async (e) => {
  e.target.disabled = true;
  const { data, ok } = await api.post("/api/service/start");
  state.service = ok ? data : state.service;
  toast(data.running ? "Serviço Python iniciado" : `Não iniciou: ${data.error || (data.logs || []).slice(-1)[0] || "veja a aba Integrações"}`);
  drawService();
  if (current === "simulador") render();
});
document.getElementById("service-stop").addEventListener("click", async () => {
  const { data } = await api.post("/api/service/stop");
  state.service = data;
  drawService();
  toast("Serviço parado");
});
window.addEventListener("hashchange", render);

await refreshService();
drawService();
const overview = await refreshOverview();
updateRunLabel(overview.ranAt);
render();
setInterval(async () => {
  await refreshService();
  drawService();
}, 8000);
