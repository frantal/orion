// Thin API client for the ORION backend. All calls go through the Vite proxy.

const BASE = "/api";

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch (_) {
      /* ignore */
    }
    throw new Error(detail);
  }
  return res.json();
}

export const api = {
  health: () => request("/health"),
  account: () => request("/account"),
  clock: () => request("/clock"),
  opportunities: (symbol, limit = 10) =>
    request(`/opportunities/${symbol}?limit=${limit}`),
  analyze: (opportunityId, language = "en") =>
    request("/analyze", {
      method: "POST",
      body: JSON.stringify({ opportunity_id: opportunityId, language }),
    }),
  decide: (opportunityId, language = "en") =>
    request("/decision", {
      method: "POST",
      body: JSON.stringify({ opportunity_id: opportunityId, language }),
    }),
  execute: (opportunityId, confirm) =>
    request("/execute", {
      method: "POST",
      body: JSON.stringify({ opportunity_id: opportunityId, confirm }),
    }),
  decisions: () => request("/decisions"),
  positions: () => request("/positions"),
  portfolio: () => request("/portfolio"),
  performance: () => request("/performance"),
  backtest: (symbol, samples = 3000, limit = 5) =>
    request("/backtest", {
      method: "POST",
      body: JSON.stringify({ symbol, samples, limit }),
    }),
  audit: () => request("/audit"),
};
