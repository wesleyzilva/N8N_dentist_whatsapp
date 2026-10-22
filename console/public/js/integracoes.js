import { api } from "./api.js";
import { h, pill, toast } from "./dom.js";

const rowColor = { ok: "green", missing: "red", placeholder: "yellow", warn: "yellow", info: "gray" };

function card(item, redraw) {
  const pingOut = h("div", { class: "muted tiny" });
  return h(
    "div",
    { class: "card integration" },
    h("header", {}, h("div", {}, h("strong", {}, item.name), h("div", { class: "muted tiny" }, `${item.problems.join(", ")} · fase ${item.phase}`)), pill(item.status)),
    h("div", { class: "muted" }, item.summary),
    item.details.length
      ? h(
          "div",
          { class: "kv" },
          item.details.flatMap((d) => [h("span", { class: "k" }, d.label), h("span", { style: `color: var(--${rowColor[d.status] === "gray" ? "muted" : rowColor[d.status] || "ink"})` }, d.value)]),
        )
      : null,
    item.action
      ? h(
          "div",
          {},
          h(
            "button",
            {
              class: "btn small",
              onClick: async (event) => {
                event.target.disabled = true;
                pingOut.textContent = "testando…";
                const { data } = await api.post(`/api/integrations/${item.action}`);
                pingOut.textContent = `${data.ok ? "✔" : "✖"} ${data.message}`;
                event.target.disabled = false;
              },
            },
            "Testar conexão (não envia mensagem nem gasta tokens)",
          ),
          pingOut,
        )
      : null,
    h("details", {}, h("summary", { class: "tiny muted" }, "Como colocar no ar"), h("ol", { class: "howto" }, item.howTo.map((t) => h("li", {}, t)))),
  );
}

export async function renderIntegracoes(root) {
  const holder = h("div", { class: "grid cards-2" }, h("div", { class: "card empty" }, "Verificando integrações…"));
  const refresh = h(
    "button",
    {
      class: "btn",
      onClick: async () => {
        await load();
        toast("Integrações verificadas");
      },
    },
    "Verificar de novo",
  );
  root.append(
    h("p", { class: "muted", style: "margin-bottom:12px" }, "Probes reais em localhost. Nada é enviado para fora, exceto o teste opcional do Gemini. Valores de segredos nunca são exibidos, só se estão definidos."),
    h("div", { style: "margin-bottom:12px" }, refresh),
    holder,
  );
  async function load() {
    holder.replaceChildren(h("div", { class: "card empty" }, "Verificando integrações…"));
    const { data } = await api.get("/api/integrations");
    holder.replaceChildren(...data.map((item) => card(item, load)));
  }
  await load();
}
