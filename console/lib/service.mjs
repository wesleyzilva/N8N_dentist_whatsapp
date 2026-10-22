import { spawn } from "node:child_process";
import { ROOT, findPython } from "./repo.mjs";
import { httpProbe } from "./probes.mjs";

export const SERVICE_PORT = Number(process.env.SERVICE_PORT || 8001);
export const SERVICE_URL = process.env.SERVICE_URL || `http://127.0.0.1:${SERVICE_PORT}`;

let child = null;
const logs = [];

function pushLog(chunk) {
  for (const line of String(chunk).split(/\r?\n/).filter(Boolean)) {
    logs.push(`${new Date().toISOString().slice(11, 19)} ${line}`);
  }
  while (logs.length > 200) logs.shift();
}

export async function serviceStatus() {
  const health = await httpProbe(`${SERVICE_URL}/healthz`, { timeout: 1500 });
  const body = health.json || {};
  return {
    url: SERVICE_URL,
    running: health.reachable && health.ok,
    managed: Boolean(child && child.exitCode === null),
    pid: child && child.exitCode === null ? child.pid : null,
    simulationEnabled: Boolean(body.simulation_enabled),
    calendarModes: body.calendar_modes || [],
    error: health.error || null,
    logs: logs.slice(-40),
  };
}

export async function startService() {
  const current = await serviceStatus();
  if (current.running) return { ...current, note: "serviço já estava no ar" };
  const python = findPython();
  if (!python) throw new Error("Python não encontrado. Instale Python 3.10+ ou defina PYTHON.");

  child = spawn(python.cmd, ["-m", "app.interfaces.http.intent_service"], {
    cwd: ROOT,
    env: {
      ...process.env,
      PORT: String(SERVICE_PORT),
      HOST: "127.0.0.1",
      SIMULATION_ENABLED: "1",
      PYTHONUNBUFFERED: "1",
      PYTHONDONTWRITEBYTECODE: "1",
      PYTHONIOENCODING: "utf-8",
    },
    windowsHide: true,
  });
  child.stdout.on("data", pushLog);
  child.stderr.on("data", pushLog);
  child.on("exit", (code) => pushLog(`serviço encerrou (código ${code})`));

  for (let attempt = 0; attempt < 30; attempt++) {
    await new Promise((resolve) => setTimeout(resolve, 200));
    const status = await serviceStatus();
    if (status.running) return status;
    if (child.exitCode !== null) break;
  }
  return serviceStatus();
}

export async function stopService() {
  if (child && child.exitCode === null) child.kill();
  await new Promise((resolve) => setTimeout(resolve, 300));
  return serviceStatus();
}

process.on("exit", () => {
  if (child && child.exitCode === null) child.kill();
});
