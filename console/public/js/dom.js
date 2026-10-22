export function h(tag, attrs, ...children) {
  const el = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs || {})) {
    if (value === false || value == null) continue;
    if (key === "class") el.className = value;
    else if (key.startsWith("on")) el.addEventListener(key.slice(2).toLowerCase(), value);
    else if (key === "html") throw new Error("html não permitido; use texto");
    else el.setAttribute(key, value === true ? "" : value);
  }
  for (const child of children.flat(Infinity)) {
    if (child == null || child === false) continue;
    el.append(child.nodeType ? child : document.createTextNode(String(child)));
  }
  return el;
}

export const STATUS = {
  pass: { color: "green", label: "OK" },
  warn: { color: "yellow", label: "Aviso" },
  fail: { color: "red", label: "Falha" },
  skip: { color: "gray", label: "Pulado" },
  pending: { color: "gray", label: "Pendente" },
  up: { color: "green", label: "No ar" },
  down: { color: "red", label: "Fora do ar" },
  not_configured: { color: "yellow", label: "Não configurado" },
  manual: { color: "blue", label: "Validar manualmente" },
  info: { color: "gray", label: "Informativo" },
  done: { color: "green", label: "Feito" },
  in_progress: { color: "blue", label: "Em andamento" },
  blocked: { color: "red", label: "Bloqueado" },
  planned: { color: "gray", label: "Planejado" },
  red: { color: "red", label: "Em risco" },
  yellow: { color: "yellow", label: "Atenção" },
  green: { color: "green", label: "Verificado" },
  none: { color: "gray", label: "Sem evidência" },
  gray: { color: "gray", label: "Sem evidência" },
};

export function pill(status, text) {
  const info = STATUS[status] || { color: "gray", label: status };
  return h("span", { class: `pill ${info.color}` }, text ?? info.label);
}

export function colorPill(color, text) {
  return h("span", { class: `pill ${color}` }, text);
}

export function timeAgo(iso) {
  if (!iso) return "nunca";
  const seconds = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 1000));
  if (seconds < 60) return `há ${seconds}s`;
  if (seconds < 3600) return `há ${Math.round(seconds / 60)} min`;
  if (seconds < 86400) return `há ${Math.round(seconds / 3600)} h`;
  return new Date(iso).toLocaleString("pt-BR");
}

export function toast(message) {
  const el = document.getElementById("toast");
  el.textContent = message;
  el.hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => (el.hidden = true), 3500);
}

function inline(text) {
  const out = [];
  const re = /(`[^`]+`)|(\*\*[^*]+\*\*)|(\[[^\]]+\]\([^)]+\))/g;
  let last = 0;
  let match;
  while ((match = re.exec(text))) {
    if (match.index > last) out.push(text.slice(last, match.index));
    const token = match[0];
    if (token.startsWith("`")) out.push(h("code", {}, token.slice(1, -1)));
    else if (token.startsWith("**")) out.push(h("strong", {}, token.slice(2, -2)));
    else {
      const [, label, href] = token.match(/\[([^\]]+)\]\(([^)]+)\)/);
      out.push(/^https?:/.test(href) ? h("a", { href, target: "_blank", rel: "noreferrer" }, label) : label);
    }
    last = match.index + token.length;
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
}

export function renderMarkdown(source) {
  const root = h("div", { class: "md" });
  const lines = source.replace(/\r/g, "").split("\n");
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    if (/^```/.test(line)) {
      const buf = [];
      i++;
      while (i < lines.length && !/^```/.test(lines[i])) buf.push(lines[i++]);
      i++;
      root.append(h("pre", {}, h("code", {}, buf.join("\n"))));
    } else if (/^#{1,4}\s/.test(line)) {
      const level = line.match(/^#+/)[0].length;
      root.append(h(`h${Math.min(level, 3)}`, {}, inline(line.replace(/^#+\s*/, ""))));
      i++;
    } else if (/^\|/.test(line) && /^\|[\s:|-]+\|?\s*$/.test(lines[i + 1] || "")) {
      const cells = (row) => row.replace(/^\||\|\s*$/g, "").split("|").map((c) => c.trim());
      const head = cells(line);
      i += 2;
      const rows = [];
      while (i < lines.length && /^\|/.test(lines[i])) rows.push(cells(lines[i++]));
      root.append(
        h("table", {}, h("thead", {}, h("tr", {}, head.map((c) => h("th", {}, inline(c))))), h("tbody", {}, rows.map((r) => h("tr", {}, r.map((c) => h("td", {}, inline(c))))))),
      );
    } else if (/^\s*([-*]|\d+\.)\s/.test(line)) {
      const ordered = /^\s*\d+\./.test(line);
      const items = [];
      while (i < lines.length && /^\s*([-*]|\d+\.)\s/.test(lines[i])) items.push(lines[i++].replace(/^\s*([-*]|\d+\.)\s(\[[ x]\]\s)?/, (m, a, box) => (box ? (box.includes("x") ? "☑ " : "☐ ") : "")));
      root.append(h(ordered ? "ol" : "ul", {}, items.map((t) => h("li", {}, inline(t)))));
    } else if (/^>\s?/.test(line)) {
      const buf = [];
      while (i < lines.length && /^>\s?/.test(lines[i])) buf.push(lines[i++].replace(/^>\s?/, ""));
      root.append(h("blockquote", {}, inline(buf.join(" "))));
    } else if (line.trim() === "") {
      i++;
    } else {
      const buf = [];
      while (i < lines.length && lines[i].trim() !== "" && !/^(```|#|\||>|\s*([-*]|\d+\.)\s)/.test(lines[i])) buf.push(lines[i++]);
      if (!buf.length) buf.push(lines[i++]);
      root.append(h("p", {}, inline(buf.join(" "))));
    }
  }
  return root;
}
