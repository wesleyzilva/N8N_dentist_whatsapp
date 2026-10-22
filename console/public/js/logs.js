import { api } from "./api.js";
import { colorPill, h, toast } from "./dom.js";

const REASON = { clinical: "clínico", human_requested: "pediu humana", complaint: "reclamação", doctor_check: "verificar com a dra.", message_left: "recado" };

function entryCard(e) {
  const flags = [
    e.escalation?.needed ? colorPill("red", `escalou: ${REASON[e.escalation.reason] || e.escalation.reason}`) : null,
    e.fallback?.state ? colorPill("yellow", `fallback: ${e.fallback.state}`) : null,
    e.handoff_mode ? colorPill("blue", `handoff: ${e.handoff_mode}`) : null,
    e.message_type !== "text" ? colorPill("gray", e.message_type) : null,
  ];
  return h(
    "details",
    { class: "check" },
    h(
      "summary",
      {},
      colorPill("gray", new Date(e.ts).toLocaleTimeString("pt-BR")),
      h("span", { class: "title" }, `${e.patient} · ${e.intent}`),
      h("span", { class: "sum" }, e.message ? `“${e.message}”` : "(texto não gravado)"),
      ...flags,
    ),
    h(
      "div",
      { class: "detail-list" },
      h("div", {}, h("strong", {}, "Secretária: "), e.reply_text),
      h("div", { class: "muted tiny" }, `origem ${e.source} · unidade ${e.unit || "—"} · ${e.duration_ms} ms · pode afirmar fatos: ${e.can_assert_facts} · sessão ${e.session || "—"}`),
      h("ol", { class: "trace" }, (e.trace || []).map((t) => h("li", {}, h("strong", {}, `${t.step}: `), `${t.result} `, h("span", { class: "muted" }, `— ${t.why}`)))),
    ),
  );
}

export async function renderLogs(root) {
  const holder = h("div", {});
  const info = h("div", { class: "muted tiny", style: "margin:8px 0" });

  async function load() {
    const { data } = await api.get("/api/logs?limit=150");
    info.textContent = data.exists ? `${data.total} turnos em ${data.path} (mostrando os mais recentes primeiro)` : "Nenhum turno registrado ainda. Converse no Simulador ou envie um webhook.";
    holder.replaceChildren(...(data.entries.length ? data.entries.map(entryCard) : [h("div", { class: "card empty" }, "Sem registros.")]));
  }

  root.append(
    h("p", { class: "muted" }, "Cada mensagem processada pelo serviço grava um registro com o rastro de decisões. O número do paciente é mascarado; o texto só é gravado neste modo local (LOG_MESSAGE_TEXT=1)."),
    h(
      "div",
      { style: "display:flex;gap:8px;margin:8px 0" },
      h("button", { class: "btn primary", onClick: load }, "Atualizar"),
      h("button", { class: "btn ghost", onClick: async () => { await api.post("/api/logs/clear", {}); toast("Log limpo"); await load(); } }, "Limpar"),
    ),
    info,
    holder,
  );
  await load();
}
