import { api } from "./api.js";
import { h, renderMarkdown } from "./dom.js";

export async function renderDocs(root) {
  const { data: docs } = await api.get("/api/docs");
  const list = h("div", { class: "card doc-list" });
  const content = h("div", { class: "card" }, h("div", { class: "empty" }, "Escolha um documento."));
  const areas = [...new Set(docs.map((d) => d.area))];

  async function open(path, link) {
    list.querySelectorAll("a").forEach((a) => a.classList.remove("active"));
    link?.classList.add("active");
    const { data, ok } = await api.get(`/api/doc?path=${encodeURIComponent(path)}`);
    content.replaceChildren(ok ? h("div", {}, h("div", { class: "muted tiny mono" }, path), renderMarkdown(data.markdown)) : h("div", { class: "empty" }, data.error));
  }

  for (const area of areas) {
    list.append(h("h4", {}, area));
    for (const doc of docs.filter((d) => d.area === area)) {
      const link = h("a", { href: "#docs", onClick: (e) => { e.preventDefault(); open(doc.path, link); } }, doc.title, h("small", {}, doc.path));
      list.append(link);
    }
  }
  root.append(h("div", { class: "docs" }, list, content));
}
