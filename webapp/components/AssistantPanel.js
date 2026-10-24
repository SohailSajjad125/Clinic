"use client";
import { useQueryClient } from "@tanstack/react-query";
import { AnimatePresence, motion } from "framer-motion";
import { Bot, Check, Send, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { post } from "@/lib/api";
import { tzOffset } from "@/lib/hooks";

const SUGGESTIONS = ["How do I restore a deleted patient?", "Who is waiting today?", "What can a receptionist do?"];

export default function AssistantPanel({ open, onClose }) {
  const qc = useQueryClient();
  const [msgs, setMsgs] = useState([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const end = useRef(null);
  useEffect(() => { end.current?.scrollIntoView({ behavior: "smooth" }); }, [msgs, busy]);

  async function send(content) {
    const t = content.trim();
    if (!t || busy) return;
    const next = [...msgs, { role: "user", content: t }];
    setMsgs(next); setText(""); setBusy(true);
    try {
      const r = await post("/ai/chat", { messages: next.slice(-20).map(({ role, content }) => ({ role, content })), tz_offset_minutes: tzOffset() });
      setMsgs([...next, { role: "assistant", content: r.reply || "Done.", actions: r.actions.map((a) => ({ ...a, state: "pending" })) }]);
    } catch (e) { setMsgs([...next, { role: "assistant", content: e.message, error: true }]); }
    setBusy(false);
  }
  async function decide(mi, ai, kind) {
    const set = (patch) => setMsgs((l) => l.map((m, i) => i !== mi ? m : { ...m, actions: m.actions.map((a, j) => j !== ai ? a : { ...a, ...patch }) }));
    const id = msgs[mi].actions[ai].id;
    set({ state: "working" });
    try {
      if (kind === "confirm") { const r = await post(`/ai/actions/${id}/confirm`); set({ state: "done", result: r.message }); qc.invalidateQueries(); }
      else { await post(`/ai/actions/${id}/cancel`); set({ state: "cancelled" }); }
    } catch (e) { set({ state: "error", result: e.message }); }
  }

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div className="fixed inset-0 z-[70] bg-black/40" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={onClose} />
          <motion.aside role="dialog" aria-label="ClinicOS Assistant" initial={{ x: "100%" }} animate={{ x: 0 }} exit={{ x: "100%" }} transition={{ type: "spring", stiffness: 320, damping: 34 }}
            className="fixed right-0 top-0 z-[80] flex h-full w-full max-w-md flex-col border-l border-line bg-bg shadow-2xl">
            <header className="flex items-center justify-between border-b border-line px-5 py-4">
              <div className="flex items-center gap-3"><span className="grid h-9 w-9 place-items-center rounded-full bg-primary text-primary-fg"><Bot className="h-5 w-5" /></span>
                <div><p className="font-display font-bold">ClinicOS Assistant</p><p className="text-xs text-mute">Asks before it changes anything</p></div></div>
              <button onClick={onClose} aria-label="Close assistant" className="rounded-lg p-2 hover:bg-surface"><X className="h-5 w-5" /></button>
            </header>
            <div className="flex-1 space-y-4 overflow-y-auto p-5">
              {msgs.length === 0 && (
                <div><p className="text-mute">Ask how something works, or tell me what to do, like "Book Ali Hassan tomorrow at 5 pm".</p>
                  <div className="mt-4 flex flex-wrap gap-2">{SUGGESTIONS.map((s) => <button key={s} onClick={() => send(s)} className="rounded-full border border-line bg-surface px-3 py-1.5 text-sm hover:border-brand">{s}</button>)}</div></div>
              )}
              {msgs.map((m, mi) => (
                <motion.div key={mi} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className={m.role === "user" ? "flex justify-end" : ""}>
                  <div className={`max-w-[92%] whitespace-pre-wrap rounded-2xl px-4 py-2.5 text-sm leading-6 ${m.role === "user" ? "bg-primary text-primary-fg" : m.error ? "border border-danger/40 text-danger-ink" : "border border-line bg-surface"}`}>
                    {m.content}
                    {m.actions?.map((a, ai) => (
                      <div key={a.id} className="mt-3 rounded-xl border border-line bg-bg p-3">
                        <p className="font-medium">{a.summary}</p>
                        {a.state === "pending" && <div className="mt-2 flex gap-2"><button className="btn btn-primary btn-sm" onClick={() => decide(mi, ai, "confirm")}>Confirm</button><button className="btn btn-outline btn-sm" onClick={() => decide(mi, ai, "cancel")}>Cancel</button></div>}
                        {a.state === "working" && <p className="mt-2 text-xs text-mute">Working…</p>}
                        {a.state === "done" && <p className="mt-2 flex items-center gap-1 text-xs font-medium text-success-ink"><Check className="h-3.5 w-3.5" />{a.result}</p>}
                        {a.state === "cancelled" && <p className="mt-2 text-xs text-mute">Cancelled. Nothing was changed.</p>}
                        {a.state === "error" && <p role="alert" className="mt-2 text-xs text-danger-ink">{a.result}</p>}
                      </div>
                    ))}
                  </div>
                </motion.div>
              ))}
              {busy && <div className="flex gap-1 px-2" aria-label="Assistant is thinking">{[0, 1, 2].map((i) => <motion.i key={i} className="h-2 w-2 rounded-full bg-mute" animate={{ opacity: [0.3, 1, 0.3] }} transition={{ repeat: Infinity, duration: 1, delay: i * 0.15 }} />)}</div>}
              <div ref={end} />
            </div>
            <form onSubmit={(e) => { e.preventDefault(); send(text); }} className="flex gap-2 border-t border-line p-4">
              <label htmlFor="ai-input" className="sr-only">Message</label>
              <input id="ai-input" value={text} onChange={(e) => setText(e.target.value)} placeholder="Ask or tell me what to do…" maxLength={2000} className="field" autoFocus />
              <button className="btn btn-primary px-3.5" disabled={busy || !text.trim()} aria-label="Send"><Send className="h-4 w-4" /></button>
            </form>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
}
