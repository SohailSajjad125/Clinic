"use client";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { Bot, Check } from "lucide-react";
import { useEffect, useState } from "react";

const SCRIPT = [
  { who: "user", text: "Book Ali Hassan tomorrow at 5 pm with Dr. Noor." },
  { who: "bot", text: "Ali Hassan · Dr. Noor · tomorrow, 5:00 pm. Shall I book it?", confirm: true },
  { who: "user", text: "Yes, go ahead." },
  { who: "bot", text: "Booked. A reminder will go to Ali this evening.", done: true },
  { who: "user", text: "How do I restore a patient I deleted?" },
  { who: "bot", text: "Open Deleted history, select the patient and choose Restore." },
];

export default function AssistantDemo() {
  const reduce = useReducedMotion();
  const [n, setN] = useState(reduce ? SCRIPT.length : 1);
  useEffect(() => {
    if (reduce) { setN(SCRIPT.length); return; }
    const t = setTimeout(() => setN((c) => (c >= SCRIPT.length ? 1 : c + 1)), n >= SCRIPT.length ? 5000 : 1900);
    return () => clearTimeout(t);
  }, [n, reduce]);

  return (
    <div className="rounded-2xl border border-line bg-surface p-5 shadow-xl" role="img" aria-label="Example conversation with the ClinicOS Assistant">
      <div className="mb-4 flex items-center gap-2.5 border-b border-line pb-4">
        <span className="grid h-8 w-8 place-items-center rounded-full bg-primary text-primary-fg"><Bot className="h-4 w-4" /></span>
        <div><p className="text-sm font-semibold">ClinicOS Assistant</p><p className="text-xs text-mute">Example conversation</p></div>
      </div>
      <div className="flex min-h-[320px] flex-col justify-end gap-3">
        <AnimatePresence initial={false}>
          {SCRIPT.slice(0, n).map((m, i) => (
            <motion.div key={i} layout={!reduce} initial={reduce ? false : { opacity: 0, y: 12, scale: 0.98 }} animate={{ opacity: 1, y: 0, scale: 1 }} transition={{ duration: 0.3 }}
              className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm leading-6 ${m.who === "user" ? "self-end bg-primary text-primary-fg" : "self-start border border-line bg-bg"}`}>
              {m.text}
              {m.confirm && n === i + 1 && <span className="mt-2 flex gap-2"><span className="rounded-lg bg-primary px-3 py-1 text-xs font-semibold text-primary-fg">Confirm</span><span className="rounded-lg border border-line px-3 py-1 text-xs font-semibold">Cancel</span></span>}
              {m.done && <span className="mt-1 flex items-center gap-1 text-xs font-medium text-brand"><Check className="h-3.5 w-3.5" /> Logged in the audit trail</span>}
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
}
