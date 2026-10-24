"use client";
import { Bell, Check, Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useConfirm } from "@/components/Modal";
import { Empty, ErrorBox, PageHeader, Skeleton } from "@/components/ui";
import { del, post } from "@/lib/api";
import { fmtDateTime, useAct, useApi } from "@/lib/hooks";

export default function Notifications() {
  const router = useRouter();
  const act = useAct();
  const confirm = useConfirm();
  const list = useApi("notifications", "/notifications", { staleTime: 0 });
  const items = list.data?.items || [];
  const inv = { invalidate: ["notifications"] };
  async function clearAll() {
    if (await confirm({ title: "Clear all notifications?", body: "They'll be deleted permanently.", action: "Clear all", danger: true })) act(() => del("/notifications"), { ...inv, ok: "Notifications cleared" });
  }
  return (
    <>
      <PageHeader title="Notifications" sub={list.data ? `${list.data.unread} unread` : ""}>
        <button className="btn btn-outline" disabled={!list.data?.unread} onClick={() => act(() => post("/notifications/read-all"), inv)}><Check className="h-4 w-4" />Mark all read</button>
        <button className="btn btn-outline" disabled={!items.length} onClick={clearAll}><Trash2 className="h-4 w-4" />Clear all</button>
      </PageHeader>
      <ErrorBox error={list.error} />
      {list.isLoading ? <Skeleton /> : items.length === 0 ? <Empty icon={Bell} title="You're all caught up" hint="Arrivals, payments and other updates show up here." /> : (
        <div className="card divide-y divide-line">{items.map((n) => (
          <div key={n.id} className={`flex items-start justify-between gap-3 px-5 py-4 ${n.read ? "" : "bg-[color-mix(in_srgb,var(--primary)_6%,transparent)]"}`}>
            <div className="flex gap-3">{!n.read && <span className="mt-2 h-2 w-2 shrink-0 rounded-full bg-brand" aria-label="Unread" />}<div className={n.link ? "cursor-pointer" : ""} onClick={() => { if (n.link) { post(`/notifications/${n.id}/read`).catch(() => {}); router.push(n.link); } }}><p className="font-semibold">{n.title}</p>{n.body && <p className="text-sm text-mute">{n.body}</p>}<p className="mt-1 text-xs text-mute">{fmtDateTime(n.created_at)}</p></div></div>
            <div className="flex gap-1">{!n.read && <button aria-label="Mark as read" onClick={() => act(() => post(`/notifications/${n.id}/read`), inv)} className="rounded-lg p-2 text-mute hover:bg-bg hover:text-brand"><Check className="h-4 w-4" /></button>}
              <button aria-label="Delete notification" onClick={() => act(() => del(`/notifications/${n.id}`), inv)} className="rounded-lg p-2 text-mute hover:bg-danger/10 hover:text-danger-ink"><Trash2 className="h-4 w-4" /></button></div></div>))}</div>
      )}
    </>
  );
}
