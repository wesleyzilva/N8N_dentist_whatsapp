async function request(method, path, body) {
  const response = await fetch(path, {
    method,
    headers: method === "POST" ? { "Content-Type": "application/json", "X-TPM-Console": "1" } : {},
    body: method === "POST" ? JSON.stringify(body || {}) : undefined,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok && !data.error) data.error = `HTTP ${response.status}`;
  return { ok: response.ok, status: response.status, data };
}

export const api = {
  get: (path) => request("GET", path),
  post: (path, body) => request("POST", path, body),
};

export const state = { overview: null, service: null };

export async function refreshOverview() {
  const { data } = await api.get("/api/overview");
  state.overview = data;
  return data;
}

export async function refreshService() {
  const { data } = await api.get("/api/service");
  state.service = data;
  return data;
}
