"use client";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { useEffect, useRef, useState } from "react";

const PEOPLE = [
  ["Ahmed Raza", "Follow-up visit"], ["Sara Malik", "New patient"], ["Ali Hassan", "Fever, 3 days"], ["Hina Farooq", "Lab report review"],
  ["Bilal Ahmad", "Dental check-up"], ["Ayesha Noor", "Skin consultation"], ["Usman Tariq", "Physiotherapy"],
];
const make = (n) => ({ id: n, name: PEOPLE[n % PEOPLE.length][0], reason: PEOPLE[n % PEOPLE.length][1] });
const BARS = [38, 52, 44, 68, 60, 82, 74];

export default function HeroPreview() {
  const reduce = useReducedMotion();
  const counter = useRef(4);
  const [queue, setQueue] = useState([0, 1, 2, 3].map(make));
  const [seen, setSeen] = useState(14);

  useEffect(() => {
    if (reduce) return;
    const t = setInterval(() => {
      const id = counter.current++;
      setQueue((q) => [...q.slice(1), make(id)]);
      setSeen((s) => s + 1);
    }, 3600);
    return () => clearInterval(t);
  }, [reduce]);

  return (
    <div className="relative w-full max-w-xl" aria-label="Live preview of the ClinicOS queue with sample data" role="img">
      <div className="rounded-2xl border border-line bg-surface p-5 shadow-2xl shadow-black/15 backdrop-blur">
        <div className="mb-4 flex items-center justify-between">
          <div className="flex gap-1.5"><i className="h-2.5 w-2.5 rounded-full bg-line" /><i className="h-2.5 w-2.5 rounded-full bg-line" /><i className="h-2.5 w-2.5 rounded-full bg-line" /></div>
          <p className="text-xs font-medium text-mute">Today · Queue</p>
        </div>
        <div className="grid gap-4 sm:grid-cols-[1.5fr_1fr]">
          <ul className="space-y-2">
            <AnimatePresence initial={false} mode="popLayout">
              {queue.map((p, i) => (
                <motion.li key={p.id} layout={!reduce} initial={reduce ? false : { opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }}
                  exit={reduce ? undefined : { opacity: 0, x: -28 }} transition={{ type: "spring", stiffness: 380, damping: 32 }}
                  className={`flex items-center justify-between rounded-xl border px-3.5 py-3 ${i === 0 ? "border-brand bg-accent-soft" : "border-line bg-bg"}`}>
                  <div className="flex items-center gap-3">
                    <span className="font-mono text-xs text-mute">#{String(p.id + 1).padStart(2, "0")}</span>
                    <div><p className="text-sm font-semibold text-ink">{p.name}</p><p className="text-xs text-mute">{p.reason}</p></div>
                  </div>
                  <span className={`flex items-center gap-1.5 text-xs font-medium ${i === 0 ? "text-brand" : "text-mute"}`}>
                    {i === 0 && <span className="relative flex h-2 w-2"><span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary opacity-60" /><span className="relative h-2 w-2 rounded-full bg-primary" /></span>}
                    {i === 0 ? "In consultation" : "Waiting"}
                  </span>
                </motion.li>
              ))}
            </AnimatePresence>
          </ul>
          <div className="space-y-3">
            <div className="rounded-xl border border-line bg-bg p-3.5">
              <p className="text-xs text-mute">Seen today</p>
              <div className="h-9 overflow-hidden"><AnimatePresence mode="popLayout" initial={false}>
                <motion.p key={seen} initial={reduce ? false : { y: 20, opacity: 0 }} animate={{ y: 0, opacity: 1 }} exit={reduce ? undefined : { y: -20, opacity: 0 }} transition={{ duration: 0.3 }}
                  className="font-display text-3xl font-extrabold text-ink">{seen}</motion.p></AnimatePresence></div>
            </div>
            <div className="rounded-xl border border-line bg-bg p-3.5">
              <p className="text-xs text-mute">Waiting now</p>
              <p className="font-display text-3xl font-extrabold text-ink">{queue.length - 1}</p>
            </div>
            <div className="flex h-16 items-end gap-1.5 rounded-xl border border-line bg-bg p-3" aria-hidden="true">
              {BARS.map((h, i) => <motion.i key={i} initial={reduce ? false : { height: 0 }} animate={{ height: `${h}%` }} transition={{ delay: 0.3 + i * 0.06, duration: 0.6, ease: "easeOut" }} className="flex-1 rounded-sm bg-primary opacity-70" />)}
            </div>
          </div>
        </div>
      </div>
      <p className="mt-3 text-center text-xs text-mute">Live preview using sample data</p>
    </div>
  );
}
