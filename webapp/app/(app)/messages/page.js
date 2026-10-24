"use client";
import { Eraser, Inbox, Send } from "lucide-react";
import { useConfirm } from "@/components/Modal";
import { useEffect, useRef, useState } from "react";
import { Empty, ErrorBox, PageHeader, Skeleton } from "@/components/ui";
import { post } from "@/lib/api";
import { fmtDateTime, useAct, useApi } from "@/lib/hooks";

export default function Messages() {
  const [sel, setSel] = useState(null);
  const [text, setText] = useState("");
  const act = useAct();
  const confirm = useConfirm();
  const end = useRef(null);
  const inbox = useApi(["portal-messages", "inbox"], "/messages/inbox");
  const thread = useApi(["portal-messages", "thread", sel], `/patients/${sel}/messages`, { enabled: !!sel, staleTime: 0 });
  useEffect(() => { end.current?.scrollIntoView({ behavior: "smooth" }); }, [thread.data?.length]);
  async function clearThread() {
    if (await confirm({ title: "Clear this chat?", body: "It disappears from your screen only. The patient and your colleagues still see it.", action: "Clear chat" }))
      act(() => post(`/patients/${sel}/messages/clear`), { ok: "Chat cleared from your view", invalidate: ["portal-messages", "dots"] });
  }
  async function send(e) {
    e.preventDefault();
    const body = text.trim();
    if (!body) return;
    setText("");
    if (!(await act(() => post(`/patients/${sel}/messages`, { body }), { invalidate: ["portal-messages"] }))) setText(body);
  }
  return (
    <>
      <PageHeader title="Patient messages" sub="Conversations with patients who use the portal. Patients can be given access from their profile." />
      <ErrorBox error={inbox.error} />
      {inbox.isLoading ? <Skeleton /> : inbox.data.length === 0 ? <Empty icon={Inbox} title="No messages yet" hint="When a patient writes from the portal, it shows up here." /> : (
        <div className="grid gap-4 lg:grid-cols-[320px_1fr]">
          <ul className="card max-h-[60vh] divide-y divide-line overflow-y-auto">{inbox.data.map((c) => (
            <li key={c.patient_id}><button onClick={() => setSel(c.patient_id)} className={`w-full px-4 py-3 text-left hover:bg-bg ${sel === c.patient_id ? "bg-accent-soft" : ""}`}>
              <span className="flex items-center justify-between"><span className="font-semibold">{c.patient_name}</span>{c.unread > 0 && <span className="grid h-5 min-w-5 place-items-center rounded-full bg-danger px-1 text-[10px] font-bold text-danger-fg">{c.unread}</span>}</span>
              <span className="block truncate text-sm text-mute">{c.last}</span></button></li>))}</ul>
          <div className="card flex h-[60vh] flex-col">
            {!sel ? <p className="m-auto text-mute">Select a conversation.</p> : (<>
              <div className="flex items-center justify-between border-b border-line px-5 py-3"><p className="font-semibold">{inbox.data.find((c) => c.patient_id === sel)?.patient_name || "Conversation"}</p>
                <button className="btn btn-outline btn-sm" onClick={clearThread}><Eraser className="h-3.5 w-3.5" />Clear chat</button></div>
              <div className="flex-1 space-y-3 overflow-y-auto p-5">{(thread.data || []).map((m) => (
                <div key={m.id} className={`flex ${m.from_patient ? "" : "justify-end"}`}><div className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm ${m.from_patient ? "border border-line bg-bg" : "bg-primary text-primary-fg"}`}>
                  <p className={`text-xs ${m.from_patient ? "text-mute" : "text-primary-fg opacity-75"}`}>{m.sender_name} · {fmtDateTime(m.created_at)}</p><p className="whitespace-pre-wrap break-words leading-6">{m.body}</p></div></div>))}<div ref={end} /></div>
              <form onSubmit={send} className="flex gap-2 border-t border-line p-4"><label htmlFor="reply" className="sr-only">Reply</label><input id="reply" value={text} onChange={(e) => setText(e.target.value)} maxLength={2000} placeholder="Write a reply…" className="field" autoComplete="off" />
                <button className="btn btn-primary px-4" disabled={!text.trim()} aria-label="Send"><Send className="h-4 w-4" /></button></form></>)}
          </div>
        </div>)}
    </>
  );
}
