// API helpers. In production the frontend is served by FastAPI, so relative
// paths hit the same origin; in dev, Vite proxies /api to localhost:8000.
async function req(path, opts) {
  const r = await fetch(path, opts);
  if (!r.ok) throw new Error(`${path} -> ${r.status}`);
  return r.json();
}
export const get = (path) => req(path);
export const post = (path, body) =>
  req(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
