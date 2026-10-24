export const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
export const WS_URL = API.replace(/^http/, "ws") + "/ws";
export const SITE = process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000";

const ls = (fn) => { try { return fn(); } catch { return null; } };
export const session = {
  get access() { return typeof window === "undefined" ? null : ls(() => localStorage.getItem("cos_access")); },
  get refresh() { return typeof window === "undefined" ? null : ls(() => localStorage.getItem("cos_refresh")); },
  set(t) { ls(() => { localStorage.setItem("cos_access", t.access_token); localStorage.setItem("cos_refresh", t.refresh_token); }); },
  clear() { ls(() => { localStorage.removeItem("cos_access"); localStorage.removeItem("cos_refresh"); }); },
};

async function raw(path, opts = {}, token = session.access) {
  let res;
  try {
    res = await fetch(`${API}${path}`, { ...opts, headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}), ...opts.headers } });
  } catch { throw Object.assign(new Error("Can't reach the server. Check your connection."), { status: 0 }); }
  if (res.status === 204) return null;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const first = Array.isArray(data.detail) ? String(data.detail[0]?.msg || "").replace(/^Value error, /, "") : "";
    const msg = Array.isArray(data.detail) ? first || "Please check the form and try again." : data.detail;
    throw Object.assign(new Error(msg || "Something went wrong. Try again."), { status: res.status });
  }
  return data;
}

const PUBLIC = ["/auth/login", "/auth/register-clinic", "/auth/refresh"];
export async function api(path, opts) {
  try { return await raw(path, opts); }
  catch (e) {
    if (e.status !== 401 || !session.refresh || PUBLIC.includes(path)) throw e;
    try {
      const fresh = await raw("/auth/refresh", { method: "POST", body: JSON.stringify({ refresh_token: session.refresh }) }, null);
      session.set(fresh);
      return await raw(path, opts, fresh.access_token);
    } catch (e2) { if (e2.status === 401) session.clear(); throw e2.status === 401 ? e : e2; }
  }
}
export const post = (path, body) => api(path, { method: "POST", body: JSON.stringify(body ?? {}) });
export const patch = (path, body) => api(path, { method: "PATCH", body: JSON.stringify(body) });
export const del = (path) => api(path, { method: "DELETE" });

/** Fetch a protected file (PDF, download) with the access token and open or save it. */
export async function openFile(path, { download = false, name = "file" } = {}) {
  try { await api("/auth/me"); } catch { /* refresh happens inside api() */ }
  const res = await fetch(`${API}${path}`, { headers: { Authorization: `Bearer ${session.access}` } });
  if (!res.ok) throw new Error(res.status === 404 ? "File not found." : "Couldn't open the file.");
  const url = URL.createObjectURL(await res.blob());
  if (download) { const a = document.createElement("a"); a.href = url; a.download = name; a.click(); }
  else window.open(url, "_blank", "noopener");
  setTimeout(() => URL.revokeObjectURL(url), 60_000);
}
export async function upload(path, formData) {
  try { await api("/auth/me"); } catch {}
  const res = await fetch(`${API}${path}`, { method: "POST", headers: { Authorization: `Bearer ${session.access}` }, body: formData });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Upload failed.");
  return data;
}
