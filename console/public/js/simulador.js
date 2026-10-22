import { api, refreshService, state } from "./api.js";
import { colorPill, h, toast } from "./dom.js";

const PRESETS = [
  ["Pato Branco (DDD 46)", "5546999887766"],
  ["São Carlos (DDD 16)", "5516999887766"],
  ["Outro DDD (11)", "5511999887766"],
];
const QUICK = [
  "Olá",
  "Vou confirmar minha consulta",
  "Quero reagendar para outro dia",
  "Quero cancelar",
  "Quero ver disponibilidade",
  "Pode ser qualquer horário amanhã",
  "A dra está em Pato Branco?",
  "A dra está em São Carlos hoje?",
  "Quanto custa o preenchimento?",
  "Estou com dor e inchaço",
  "Quero falar com uma pessoa",
  "Sim",
  "Pato Branco",
  "parar",
];
const CLOCK = /\b\d{1,2}\s*(?::\d{2}|h\b|h\d{2})/gi;
const CITIES = ["pato branco", "são carlos", "sao carlos"];

export const sim = {
  number: PRESETS[0][1],
  calendarMode: "missing",
  fixtureCity: "São Carlos",
  target: "python",
  messages: [],
  selected: null,
};

export function lintResponse(resp) {
  const reply = String(resp?.reply_text || "");
  const notes = [];
  const evidenceText = JSON.stringify(resp?.availability_evidence ?? "");
  const hasAvailability = resp?.availability_evidence && resp.availability_evidence !== "missing";
  const hasPresence = resp?.presence_evidence && resp.presence_evidence !== "missing";
  const times = reply.match(CLOCK) || [];
  if (times.length && !hasAvailability) notes.push({ level: "bad", text: `Horário citado sem evidência de agenda: ${times.join(", ")}` });
  if (times.length && hasAvailability) {
    const outside = times.filter((t) => !evidenceText.replace(/\s/g, "").includes(t.replace(/\s/g, "")));
    if (outside.length) notes.push({ level: "bad", text: `Horário fora do retorno da ferramenta: ${outside.join(", ")}` });
  }
  const mentioned = CITIES.filter((c) => reply.toLowerCase().includes(c));
  const talksAboutDra = resp?.intent === "LOCATION" || /\bdra\b/i.test(reply);
  if (mentioned.length && talksAboutDra && !hasPresence && !/nessa unidade|prefere|Combinado/i.test(reply)) {
    notes.push({ level: "bad", text: "Cidade da dra afirmada sem evidência de presença" });
  }
  if (resp?.escalation?.needed) notes.push({ level: "info", text: "Escalou para humana" });
  if (!notes.some((n) => n.level === "bad")) notes.unshift({ level: "ok", text: "Grounded: sem fato inventado" });
  return notes;
}

function badges(resp) {
  if (!resp || resp.error) return null;
  const unit = resp.unit_hypothesis;
  const items = [];
  if (resp.intent) items.push(colorPill("blue", resp.intent));
  if (unit?.unit_id) items.push(colorPill("gray", `unidade? ${unit.unit_id}${unit.needs_confirmation ? " (a confirmar)" : ""}`));
  for (const note of lintResponse(resp)) items.push(colorPill(note.level === "ok" ? "green" : note.level === "bad" ? "red" : "yellow", note.text));
  return h("div", { class: "badges" }, items);
}

function inspectorRow(name, value, extra) {
  return h("div", { class: "row" }, h("div", { class: "name" }, h("span", {}, name), extra ? h("span", { class: "extra" }, extra) : null), h("div", { class: "val" }, value));
}

function inspector(message) {
  const box = h("div", { class: "card inspector" }, h("h3", {}, "Contrato da resposta"));
  const resp = message?.response;
  if (!resp) {
    box.append(h("p", { class: "muted" }, "Envie uma mensagem e clique em uma resposta da secretária para inspecionar."));
    return box;
  }
  if (resp.error) {
    box.append(h("div", { class: "banner red" }, resp.error), resp.hint ? h("p", { class: "muted tiny" }, resp.hint) : null);
    return box;
  }
  const data = resp.response && resp.target ? resp.response : resp;
  const unit = data.unit_hypothesis || {};
  const claims = data.allowed_claims || {};
  const tools = data.tool_status || {};
  const missing = (v) => v === "missing" || v == null;
  box.append(
    h("div", { class: "muted tiny" }, `${resp.target === "n8n" ? "n8n" : "Python"} · ${resp.endpoint || ""} · ${resp.ms ?? "?"} ms`),
    inspectorRow("1 · intent", `${data.intent ?? "—"} (${data.confidence ?? "?"})`),
    inspectorRow("2 · unit_hypothesis", unit.unit_id ? `${unit.unit_id} · fonte ${unit.source} · DDD ${unit.patient_ddd ?? "?"}${unit.conflict ? " · CONFLITO texto×DDD" : ""} · is_presence=${unit.is_presence}` : "sem hipótese (perguntar cidade)"),
    inspectorRow("3 · presence_evidence", missing(data.presence_evidence) ? "missing" : JSON.stringify(data.presence_evidence), colorPill(missing(data.presence_evidence) ? "yellow" : "green", missing(data.presence_evidence) ? "sem evidência" : "da ferramenta")),
    inspectorRow("4 · availability_evidence", missing(data.availability_evidence) ? "missing" : JSON.stringify(data.availability_evidence), colorPill(missing(data.availability_evidence) ? "yellow" : "green", missing(data.availability_evidence) ? "sem evidência" : "da ferramenta")),
    inspectorRow("5 · allowed_claims", h("div", { class: "chips" }, (claims.allowed || []).map((c) => colorPill("green", c)), (claims.blocked || []).map((c) => colorPill("red", `bloqueada: ${c}`)), !(claims.allowed || []).length && !(claims.blocked || []).length ? "nenhuma claim solicitada" : null), `can_assert_facts=${data.can_assert_facts}`),
    inspectorRow("6 · escalation", data.escalation?.needed ? `SIM — ${data.escalation.reason}` : "não"),
    inspectorRow("ferramenta de calendário", tools.calendar_mode ? `modo ${tools.calendar_mode} · freebusy ${tools.freebusy} · presença ${tools.presence}` : "não informado"),
    inspectorRow("sessão (memória curta)", data.session ? `${data.session.brief || "—"}${data.session.pending ? ` · pendente ${data.session.pending}` : ""}` : "—"),
    inspectorRow("fallback (fora do mapa)", data.fallback ? `${data.fallback.state}${data.fallback.reason ? ` · motivo ${data.fallback.reason}` : ""}` : "não acionado"),
    data.handoff ? inspectorRow("handoff para a equipe/n8n", `${data.handoff.mode} · ${data.handoff.reason || ""}${data.handoff.message ? ` · mensagem: ${data.handoff.message}` : ""}${data.handoff.media_type ? ` · mídia: ${data.handoff.media_type}` : ""}`) : null,
    h("div", { class: "extra" }, h("strong", {}, "Rastro de decisões"), h("ol", { class: "trace" }, (data.trace || []).map((t) => h("li", {}, h("strong", {}, `${t.step}: `), `${t.result} `, h("span", { class: "muted" }, `— ${t.why}`))))),
    inspectorRow("lint de grounding", h("div", { class: "chips" }, lintResponse(data).map((n) => colorPill(n.level === "ok" ? "green" : n.level === "bad" ? "red" : "yellow", n.text)))),
    h("details", {}, h("summary", { class: "tiny muted" }, "JSON bruto"), h("pre", { class: "json" }, JSON.stringify(resp.response ?? resp, null, 2))),
  );
  return box;
}

function scenarioStub() {
  const turns = [];
  for (let i = 0; i < sim.messages.length; i++) {
    const m = sim.messages[i];
    if (m.role !== "patient") continue;
    const reply = sim.messages[i + 1];
    const data = reply?.response?.response || reply?.response;
    const expect = {};
    if (data?.intent) expect.intent = data.intent;
    if (data) {
      expect.availability = data.availability_evidence && data.availability_evidence !== "missing" ? "present" : "missing";
      expect.presence = data.presence_evidence && data.presence_evidence !== "missing" ? "present" : "missing";
      if (data.escalation?.needed) expect.escalation = true;
    }
    turns.push({ say: m.text, expect });
  }
  return { id: "SNN-novo-cenario", title: "Descreva o que este cenário prova", problems: ["P2"], phase: 1, number: sim.number, calendar_mode: sim.calendarMode, ...(sim.calendarMode === "fixture" ? { fixture_city: sim.fixtureCity } : {}), turns };
}

export async function renderSimulador(root) {
  const service = state.service || (await refreshService());
  const side = h("div", { class: "sim-side" });
  const phoneHolder = h("div", {});
  const inspectorHolder = h("div", {});
  const banner = h("div", {});

  function drawBanner() {
    banner.replaceChildren();
    if (sim.target === "python" && !service.running) banner.append(h("div", { class: "banner red" }, "Serviço Python fora do ar. Use 'Iniciar serviço' na barra lateral."));
    else if (sim.target === "python" && !service.simulationEnabled && sim.calendarMode !== "missing") banner.append(h("div", { class: "banner red" }, "O serviço em execução não é o do Console (sem simulação). Pare-o e inicie pelo Console."));
    else if (sim.target === "n8n") banner.append(h("div", { class: "banner blue" }, "Alvo n8n: teste de ponta a ponta pelo webhook. O modo de calendário não se aplica (o n8n decide)."));
    else if (sim.calendarMode === "fixture") banner.append(h("div", { class: "banner yellow" }, `FIXTURE: a ferramenta devolve horários e presença (${sim.fixtureCity || "sem presença"}) de teste. Simula a Fase 3; não são fatos reais.`));
    else if (sim.calendarMode === "error") banner.append(h("div", { class: "banner yellow" }, "Ferramenta de calendário simulada com ERRO: a secretária deve pedir espera ou escalar."));
    else banner.append(h("div", { class: "banner blue" }, "Sem ferramenta de calendário (estado real do MVP): nenhum horário nem cidade da dra pode ser afirmado."));
  }

  function drawSide() {
    side.replaceChildren(
      h(
        "div",
        { class: "card" },
        h("h3", {}, "Paciente"),
        h("div", { class: "field", style: "margin-top:10px" }, h("label", {}, "Número WhatsApp"), h("input", { type: "text", value: sim.number, onInput: (e) => (sim.number = e.target.value.replace(/\D/g, "")) })),
        h("div", { class: "chips", style: "margin-top:8px" }, PRESETS.map(([label, number]) => h("button", { class: "chip", onClick: () => { sim.number = number; drawSide(); } }, label))),
        h("p", { class: "muted tiny", style: "margin-top:8px" }, "O DDD é só hipótese de unidade, nunca prova de onde a dra está."),
      ),
      h(
        "div",
        { class: "card" },
        h("h3", {}, "Ferramenta de calendário"),
        h(
          "div",
          { class: "radio", style: "margin-top:10px" },
          [["missing", "Sem ferramenta (padrão do MVP)"], ["error", "Ferramenta com erro"], ["fixture", "Fixture (simula Fase 3)"]].map(([value, label]) =>
            h("label", {}, h("input", { type: "radio", name: "cal", value, checked: sim.calendarMode === value, onChange: () => { sim.calendarMode = value; drawSide(); drawBanner(); } }), label),
          ),
        ),
        sim.calendarMode === "fixture"
          ? h("div", { class: "field", style: "margin-top:10px" }, h("label", {}, "Presença da dra no fixture"), h("select", { onChange: (e) => { sim.fixtureCity = e.target.value; drawBanner(); } }, ["São Carlos", "Pato Branco", ""].map((c) => h("option", { value: c, selected: sim.fixtureCity === c }, c || "sem evento de presença"))))
          : null,
      ),
      h(
        "div",
        { class: "card" },
        h("h3", {}, "Alvo"),
        h("div", { class: "field", style: "margin-top:10px" }, h("select", { onChange: (e) => { sim.target = e.target.value; drawBanner(); } }, [["python", "Python /turn (direto)"], ["n8n", "n8n webhook (ponta a ponta)"]].map(([v, l]) => h("option", { value: v, selected: sim.target === v }, l)))),
        h("div", { style: "display:flex;gap:6px;margin-top:10px;flex-wrap:wrap" }, h("button", { class: "btn small", onClick: newConversation }, "Nova conversa"), h("button", { class: "btn small ghost", onClick: copyScenario }, "Copiar como cenário")),
      ),
      h("div", { class: "card" }, h("h3", {}, "Mensagens rápidas"), h("div", { class: "chips", style: "margin-top:10px" }, QUICK.map((q) => h("button", { class: "chip", onClick: () => send(q) }, q)))),
    );
  }

  let messagesEl;
  let inputEl;
  function drawPhone() {
    messagesEl = h(
      "div",
      { class: "messages" },
      sim.messages.length ? null : h("div", { class: "typing" }, "Envie uma mensagem como se fosse o paciente."),
      sim.messages.map((m, idx) =>
        h(
          "div",
          { class: `msg ${m.role} ${sim.selected === idx ? "selected" : ""}`, onClick: () => { if (m.role === "secretary") { sim.selected = idx; drawPhone(); drawInspector(); } } },
          m.text,
          m.role === "secretary" ? badges(m.response?.response || m.response) : null,
        ),
      ),
    );
    inputEl = h("input", { type: "text", placeholder: "Mensagem do paciente…", onKeydown: (e) => { if (e.key === "Enter") send(inputEl.value); } });
    phoneHolder.replaceChildren(
      h(
        "div",
        { class: "card phone" },
        h("div", { class: "phone-head" }, h("div", { class: "avatar" }, "S"), h("div", {}, h("strong", {}, "Secretária da Dra. (simulação)"), h("small", {}, `paciente ${sim.number}`))),
        messagesEl,
        h("div", { class: "composer" }, inputEl, h("button", { class: "btn primary", onClick: () => send(inputEl.value) }, "Enviar")),
      ),
    );
    messagesEl.scrollTop = messagesEl.scrollHeight;
    inputEl.focus();
  }

  function drawInspector() {
    inspectorHolder.replaceChildren(inspector(sim.messages[sim.selected]));
  }

  async function send(text) {
    const message = String(text || "").trim();
    if (!message) return;
    sim.messages.push({ role: "patient", text: message });
    drawPhone();
    const typing = h("div", { class: "typing" }, "digitando…");
    messagesEl.append(typing);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    const { data } = await api.post("/api/simulate", { message, number: sim.number, calendar_mode: sim.calendarMode, fixture_city: sim.fixtureCity, target: sim.target });
    const body = data.response && data.target ? data.response : data;
    const reply = data.error ? `⚠ ${data.error}` : body.reply_text ?? body.reply ?? JSON.stringify(body).slice(0, 240);
    sim.messages.push({ role: "secretary", text: reply, response: data });
    sim.selected = sim.messages.length - 1;
    drawPhone();
    drawInspector();
  }

  async function newConversation() {
    await api.post("/api/simulate/reset", { number: sim.number });
    sim.messages = [];
    sim.selected = null;
    drawPhone();
    drawInspector();
    toast("Conversa e memória curta do paciente reiniciadas");
  }

  async function copyScenario() {
    const text = JSON.stringify(scenarioStub(), null, 2);
    try {
      await navigator.clipboard.writeText(text);
      toast("Cenário copiado. Cole em tests/scenarios/conversations.json");
    } catch {
      window.prompt("Copie o cenário:", text);
    }
  }

  drawBanner();
  drawSide();
  drawPhone();
  drawInspector();
  root.append(banner, h("div", { class: "sim", style: "margin-top:12px" }, side, phoneHolder, inspectorHolder));
  window.__simSend = send;
}

export async function replay(scenario) {
  sim.number = scenario.number;
  sim.calendarMode = scenario.calendar_mode || "missing";
  sim.fixtureCity = scenario.fixture_city ?? "São Carlos";
  sim.target = "python";
  sim.messages = [];
  sim.selected = null;
  await api.post("/api/simulate/reset", { number: sim.number });
  sim.pending = scenario.turns.map((t) => t.say);
}
