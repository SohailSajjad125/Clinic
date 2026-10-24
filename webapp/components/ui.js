"use client";
import { motion } from "framer-motion";
import { useEffect, useState } from "react";

export function PageHeader({ title, sub, children }) {
  return (
    <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
      <div><h1 className="font-display text-3xl font-extrabold tracking-tight">{title}</h1>{sub && <p className="mt-1 text-mute">{sub}</p>}</div>
      <div className="flex flex-wrap gap-2">{children}</div>
    </div>
  );
}
export function Field({ label, children, hint }) {
  return <label className="block"><span className="mb-1.5 block text-sm font-medium">{label}</span>{children}{hint && <span className="mt-1 block text-xs text-mute">{hint}</span>}</label>;
}
const tones = {
  booked: "bg-line text-mute", requested: "bg-warning/15 text-warning-ink", confirmed: "bg-accent-soft text-brand", arrived: "bg-warning/15 text-warning-ink", in_consultation: "bg-accent-soft text-brand",
  completed: "bg-success/15 text-success-ink", cancelled: "bg-danger/15 text-danger-ink", no_show: "bg-danger/15 text-danger-ink",
  pending: "bg-warning/15 text-warning-ink", partial: "bg-accent-soft text-brand", paid: "bg-success/15 text-success-ink", refunded: "bg-line text-mute",
};
export const Badge = ({ s }) => <span className={`inline-block whitespace-nowrap rounded-full px-2.5 py-1 text-xs font-semibold ${tones[s] || tones.booked}`}>{s.replace("_", " ")}</span>;
export function Empty({ icon: I, title, hint, children }) {
  return (
    <div className="card grid place-items-center px-6 py-16 text-center">
      {I && <span className="mb-4 grid h-12 w-12 place-items-center rounded-2xl bg-accent-soft text-brand"><I className="h-6 w-6" aria-hidden="true" /></span>}
      <p className="font-display text-lg font-bold">{title}</p>{hint && <p className="mt-1 max-w-sm text-mute">{hint}</p>}<div className="mt-5">{children}</div>
    </div>
  );
}
export const Skeleton = ({ rows = 4 }) => <div className="space-y-3" aria-busy="true">{Array.from({ length: rows }).map((_, i) => <div key={i} className="skeleton h-14" />)}</div>;
export const ErrorBox = ({ error }) => error ? <p role="alert" className="card border-danger/40 p-4 text-sm text-danger-ink">{error.message}</p> : null;

export function Counter({ value, format = (v) => String(Math.round(v)) }) {
  const [v, setV] = useState(0);
  useEffect(() => {
    const t0 = performance.now(), from = 0, to = Number(value) || 0;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) { setV(to); return; }
    let raf; const tick = (t) => { const p = Math.min((t - t0) / 700, 1); setV(from + (to - from) * (1 - Math.pow(1 - p, 3))); if (p < 1) raf = requestAnimationFrame(tick); };
    raf = requestAnimationFrame(tick); return () => cancelAnimationFrame(raf);
  }, [value]);
  return <>{format(v)}</>;
}
export function Stat({ label, value, format, tone }) {
  return (
    <motion.div whileHover={{ y: -2 }} className="card p-5">
      <p className="text-sm text-mute">{label}</p>
      <p className={`mt-2 font-display text-3xl font-extrabold tracking-tight ${tone || ""}`}><Counter value={value} format={format} /></p>
    </motion.div>
  );
}

export function Tabs({ tabs, value, onChange, dots = {} }) {
  return (
    <div role="tablist" className="mb-6 flex flex-wrap gap-2">
      {tabs.map(([k, l]) => <button key={k} role="tab" aria-selected={value === k} onClick={() => onChange(k)}
        className={`relative rounded-full border px-4 py-2 text-sm font-medium ${value === k ? "border-brand bg-accent-soft text-brand" : "border-line bg-surface text-mute hover:text-ink"}`}>{l}{dots[k] ? <span className="red-dot" aria-label="New activity" /> : null}</button>)}
    </div>
  );
}
