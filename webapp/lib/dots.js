"use client";
import { useQueryClient } from "@tanstack/react-query";
import { post } from "./api";
import { useApi } from "./hooks";

// Which feature (red dot category) each page belongs to.
export const ROUTE_CATEGORY = { "/appointments": "appointments", "/queue": "queue", "/patients": "patients", "/messages": "messages", "/billing": "billing", "/inventory": "inventory", "/chat": "chat", "/consultations": "consultations" };

export function useDots(enabled = true) {
  const q = useApi("dots", "/notifications/dots", { enabled, staleTime: 0 });
  const dots = q.data || {};
  return { dots, total: Object.values(dots).reduce((a, b) => a + b, 0) };
}

/** Opening a feature clears its red dot (for this person only). */
export function useSeen() {
  const qc = useQueryClient();
  return (category) => post("/notifications/seen", { category }).then(() => { qc.invalidateQueries({ queryKey: ["dots"] }); qc.invalidateQueries({ queryKey: ["notifications"] }); }).catch(() => {});
}
export const Dot = ({ show }) => (show ? <span className="red-dot" aria-label="New activity" /> : null);
