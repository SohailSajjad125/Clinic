"use client";
import { Eraser, MessagesSquare, Send, Trash2 } from "lucide-react";
import { useConfirm } from "@/components/Modal";
import { useEffect, useRef, useState } from "react";
import { Empty, ErrorBox, PageHeader, Skeleton } from "@/components/ui";
import { del, post } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { fmtTime, useAct, useApi } from "@/lib/hooks";

export default function Chat() {
  const { me } = useAuth();
  const act = useAct();
  const confirm = useConfirm();
  const [text, setText] = useState("");
  const end = useRef(null);
  const list = useApi("chat", "/chat", { staleTime: 0 });
  useEffect(() => { end.current?.scrollIntoView({ behavior: "smooth" }); }, [list.data?.length]);
  async function clearChat() {
    if (await confirm({ title: "Clear this chat?", body: "It disappears from your screen only. Everyone else in the team still sees it, and new messages will appear as usual.", action: "Clear chat" }))
      act(() => post("/chat/clear"), { ok: "Chat cleared from your view", invalidate: ["chat", "dots"] });
  }
  async function send(e) {
    e.preventDefault();
    const body = text.trim();
    if (!body) return;
    setText("");
    if (!(await act(() => post("/chat", { body }), { invalidate: ["chat"] }))) setText(body);
  }
  return (
    <>
      <PageHeader title="Team chat" sub="Messages reach everyone in the clinic instantly.">
        <button className="btn btn-outline" disabled={!list.data?.length} onClick={clearChat}><Eraser className="h-4 w-4" />Clear chat</button></PageHeader>
      <ErrorBox error={list.error} />
      <div className="card flex h-[62vh] flex-col">
        <div className="flex-1 space-y-3 overflow-y-auto p-5">
          {list.isLoading ? <Skeleton rows={3} /> : list.data?.length === 0 ? <Empty icon={MessagesSquare} title="No messages yet" hint="Say hello to your team." /> : list.data.map((m) => {
            const mine = m.sender_id === me.user_id;
            return (
              <div key={m.id} className={`group flex ${mine ? "justify-end" : ""}`}>
                <div className={`max-w-[80%] rounded-2xl px-4 py-2.5 ${mine ? "bg-primary text-primary-fg" : "border border-line bg-bg"}`}>
                  <p className={`text-xs ${mine ? "text-primary-fg opacity-75" : "text-mute"}`}>{mine ? "You" : m.sender_name} · {fmtTime(m.created_at)}</p>
                  <p className="whitespace-pre-wrap break-words text-sm leading-6">{m.body}</p></div>
                {(mine || me.role === "owner") && <button aria-label="Delete message" onClick={() => act(() => del(`/chat/${m.id}`), { invalidate: ["chat"] })} className="ml-2 self-center rounded-lg p-1.5 text-mute opacity-0 hover:text-danger-ink focus:opacity-100 group-hover:opacity-100"><Trash2 className="h-4 w-4" /></button>}
              </div>);
          })}
          <div ref={end} />
        </div>
        <form onSubmit={send} className="flex gap-2 border-t border-line p-4"><label htmlFor="msg" className="sr-only">Message</label><input id="msg" value={text} onChange={(e) => setText(e.target.value)} maxLength={2000} placeholder="Write a message…" className="field" autoComplete="off" /><button className="btn btn-primary px-4" disabled={!text.trim()} aria-label="Send"><Send className="h-4 w-4" /></button></form>
      </div>
    </>
  );
}
