import { API_URL } from "./content";

export async function postJSON(path, body) {
  let res;
  try {
    res = await fetch(`${API_URL}${path}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  } catch {
    throw new Error("We can't reach ClinicOS right now. Check your connection and try again.");
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    if (res.status === 429) throw new Error(data.detail || "Too many attempts. Please wait a few minutes.");
    if (res.status === 422) throw new Error("Please check the form and try again.");
    throw new Error("Something went wrong on our side. Please try again.");
  }
  return data;
}
