import net from "node:net";

export async function httpProbe(url, { method = "GET", body, headers = {}, timeout = 4000 } = {}) {
  const started = Date.now();
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout);
  try {
    const response = await fetch(url, {
      method,
      headers: body ? { "Content-Type": "application/json", ...headers } : headers,
      body: body ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    });
    const text = await response.text();
    let json = null;
    try {
      json = JSON.parse(text);
    } catch {
      json = null;
    }
    return { reachable: true, status: response.status, ok: response.ok, ms: Date.now() - started, text: text.slice(0, 600), json };
  } catch (error) {
    const cause = error?.cause?.code || error?.name || "erro";
    return { reachable: false, status: 0, ok: false, ms: Date.now() - started, error: cause === "AbortError" ? "timeout" : cause };
  } finally {
    clearTimeout(timer);
  }
}

export function tcpProbe(host, port, timeout = 1500) {
  return new Promise((resolve) => {
    const socket = net.createConnection({ host, port });
    const done = (reachable) => {
      socket.destroy();
      resolve({ reachable });
    };
    socket.setTimeout(timeout, () => done(false));
    socket.on("connect", () => done(true));
    socket.on("error", () => done(false));
  });
}
