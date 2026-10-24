"use client";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "./api";
import { useToast } from "@/components/Toast";

export const tzOffset = () => -new Date().getTimezoneOffset();
export const useApi = (key, path, options = {}) => useQuery({ queryKey: Array.isArray(key) ? key : [key], queryFn: () => api(path), ...options });

/** act(fn, { ok, invalidate }) runs a mutation, toasts the outcome and refreshes the lists. Returns the result or undefined on failure. */
export function useAct() {
  const qc = useQueryClient();
  const toast = useToast();
  return async (fn, { ok, invalidate = [] } = {}) => {
    try {
      const r = await fn();
      if (ok) toast(ok, "success");
      invalidate.forEach((k) => qc.invalidateQueries({ queryKey: [k] }));
      return r ?? true;
    } catch (e) { toast(e.message, "error"); return undefined; }
  };
}

export const money = (n) => `PKR ${new Intl.NumberFormat("en-PK").format(n || 0)}`;
export const fmtDate = (d) => (d ? new Date(d).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" }) : "");
export const fmtTime = (d) => new Date(d).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
export const fmtDateTime = (d) => `${fmtDate(d)}, ${fmtTime(d)}`;
export const dayKey = (d = new Date()) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
export const dayRange = (key) => { const s = new Date(`${key}T00:00:00`); const e = new Date(s.getTime() + 864e5); return `start=${encodeURIComponent(s.toISOString())}&end=${encodeURIComponent(e.toISOString())}`; };
export const toLocalInput = (d) => { const x = new Date(d.getTime() - d.getTimezoneOffset() * 6e4); return x.toISOString().slice(0, 16); };

export const CLINICAL = ["owner", "doctor", "nurse"];
export const BILLING = ["owner", "receptionist", "doctor"];
export const clean = (o) => Object.fromEntries(Object.entries(o).filter(([, v]) => v !== "" && v != null));
export const firstName = (n = "") => n.replace(/^(dr|mr|mrs|ms|prof)\.?\s+/i, "").split(" ")[0] || n;

/** A value kept in the address bar (?tab=...), so the browser Back button and our Back button walk through tabs step by step. */
export function useUrlState(key, fallback) {
  const router = useRouter();
  const path = usePathname();
  const sp = useSearchParams();
  const value = sp.get(key) || fallback;
  const set = (v) => { const p = new URLSearchParams(sp.toString()); if (v === fallback) p.delete(key); else p.set(key, v); const qs = p.toString(); router.push(qs ? `${path}?${qs}` : path, { scroll: false }); };
  return [value, set];
}
export const isoDay = (d) => dayKey(d);
export const addDays = (key, n) => { const d = new Date(`${key}T12:00:00`); d.setDate(d.getDate() + n); return dayKey(d); };
