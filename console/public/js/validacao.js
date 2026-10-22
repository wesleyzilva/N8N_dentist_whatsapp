import { api } from "./api.js";
import { h, pill, toast } from "./dom.js";

let lastRun = null;

export async function renderValidacao(root, { onRan }) {
  const { data } = await api.get("/api/checks/last");
  lastRun = data;
  const body = h("div", {});
  root.append(body);
  draw(body, onRan);
}

function draw(body, onRan) {
  body.replaceChildren();
  const results = Object.values(lastRun.results || {});
  if (!results.length) {
    body.append(h("div", { class: "card empty" }, "Nenhuma validação executada ainda. Use o botão no topo."));
    return;
  }
  const groups = [...new Set(results.map((r) => r.group))];
  for (const group of groups) {
    const items = results.filter((r) => r.group === group);
    body.append(
      h(
        "div",
        { class: "section" },
        h("h2", {}, group),
        items.map((r) =>
          h(
            "details",
            { class: "check", open: r.status === "fail" },
            h("summary", {}, pill(r.status), h("span", { class: "title" }, r.title), h("span", { class: "sum" }, r.summary, ` · ${r.durationMs} ms`)),
            h(
              "div",
              { class: "detail-list" },
              (r.details || []).length
                ? r.details.map((d) => h("div", { class: "detail-row" }, pill(d.status), h("span", {}, d.label), h("span", { class: "text" }, d.text || "")))
                : h("span", { class: "muted" }, "Sem detalhes."),
              h(
                "div",
                {},
                h(
                  "button",
                  {
                    class: "btn small ghost",
                    onClick: async (event) => {
                      event.target.disabled = true;
                      const res = await api.post("/api/checks/run", { ids: [r.id] });
                      lastRun.results = { ...lastRun.results, ...res.data.results };
                      draw(body, onRan);
                      toast(`Reexecutado: ${r.title}`);
                    },
                  },
                  "Reexecutar só esta",
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}


