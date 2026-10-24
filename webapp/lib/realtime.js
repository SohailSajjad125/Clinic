"use client";
import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect, useRef } from "react";
import { WS_URL, api, session } from "./api";
import { playChime } from "./sound";
import { useToast } from "@/components/Toast";

/** One WebSocket per signed-in person. Server events refresh the matching lists, raise a toast with a chime and light the red dot. */
export function useRealtime(enabled) {
  const qc = useQueryClient();
  const toast = useToast();
  const router = useRouter();
  const nav = useRef(router); nav.current = router;
  useEffect(() => {
    if (!enabled) return;
    let ws, timer, stop = false, retry = 0;
    const connect = async () => {
      try { await api("/auth/me"); } catch { return; }
      if (stop) return;
      ws = new WebSocket(WS_URL);
      ws.onopen = () => ws.send(JSON.stringify({ token: session.access }));
      ws.onmessage = (e) => {
        let m; try { m = JSON.parse(e.data); } catch { return; }
        if (m.type === "ready") retry = 0;
        if (m.type === "data") { qc.invalidateQueries({ queryKey: [m.entity] }); qc.invalidateQueries({ queryKey: ["analytics"] }); }
        if (m.type === "notification") {
          playChime("alert");
          toast(m.body ? `${m.title}: ${m.body}` : m.title, "info", m.link ? () => nav.current.push(m.link) : undefined);
          ["notifications", "dots", "appointments", "portal"].forEach((k) => qc.invalidateQueries({ queryKey: [k] }));
        }
        if (m.type === "chat") { playChime("soft"); qc.invalidateQueries({ queryKey: ["chat"] }); qc.invalidateQueries({ queryKey: ["dots"] }); }
        if (m.type === "portal") { qc.invalidateQueries({ queryKey: ["portal"] }); qc.invalidateQueries({ queryKey: ["dots"] }); }
      };
      ws.onclose = () => { if (!stop) timer = setTimeout(connect, Math.min(1000 * 2 ** retry++, 15000)); };
    };
    connect();
    return () => { stop = true; clearTimeout(timer); ws && ws.close(); };
  }, [enabled]); // eslint-disable-line react-hooks/exhaustive-deps
}
