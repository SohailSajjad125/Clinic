"use client";
import { RotateCcw, Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useConfirm } from "@/components/Modal";
import { Empty, ErrorBox, PageHeader, Skeleton } from "@/components/ui";
import { del, post } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { fmtDateTime, useAct, useApi } from "@/lib/hooks";

const TABS = [["patients", "Patients"], ["appointments", "Appointments"], ["consultations", "Consultations"], ["invoices", "Invoices"], ["documents", "Documents"], ["inventory", "Inventory"], ["staff", "Team"]];
const norm = (kind, r) => (kind === "staff" ? { id: r.member_id, label: `${r.full_name} · ${r.role}`, deleted_at: r.deleted_at } : r);

export default function Trash() {
  const { me } = useAuth();
  const router = useRouter();
  const [kind, setKind] = useState("patients");
  const act = useAct();
  const confirm = useConfirm();
  useEffect(() => { if (me.role !== "owner") router.replace("/dashboard"); }, [me.role, router]);
  const list = useApi(["trash", kind], `/trash/${kind}`, { enabled: me.role === "owner" });
  const rows = (list.data || []).map((r) => norm(kind, r));

  const restore = (r) => act(() => post(`/trash/${kind}/${r.id}/restore`), { ok: "Restored", invalidate: ["trash", kind, ...(kind === "staff" ? [] : [])] });
  async function purge(r) {
    const extra = kind === "patients" ? " All of this patient's appointments, consultations, invoices, documents, messages and portal login will be deleted with them." : kind === "documents" ? " The uploaded file is erased too." : "";
    if (await confirm({ title: "Delete permanently?", body: `"${r.label}" will be removed from the database. This cannot be undone.${extra}`, action: "Delete permanently", danger: true }))
      act(() => del(`/trash/${kind}/${r.id}`), { ok: "Permanently deleted", invalidate: ["trash"] });
  }
  return (
    <>
      <PageHeader title="Deleted history" sub="Restore items deleted by mistake, or remove them for good. Removing from here deletes them permanently." />
      <div role="tablist" className="mb-6 flex flex-wrap gap-2">{TABS.map(([k, l]) => <button key={k} role="tab" aria-selected={kind === k} onClick={() => setKind(k)} className={`rounded-full border px-4 py-2 text-sm font-medium ${kind === k ? "border-brand bg-accent-soft text-brand" : "border-line bg-surface text-mute hover:text-ink"}`}>{l}</button>)}</div>
      <ErrorBox error={list.error} />
      {list.isLoading ? <Skeleton /> : rows.length === 0 ? <Empty icon={Trash2} title="Nothing here" hint="Deleted items will appear here." /> : (
        <div className="card divide-y divide-line">{rows.map((r) => (
          <div key={r.id} className="flex flex-wrap items-center justify-between gap-3 px-5 py-4">
            <div><p className="font-semibold">{r.label}</p><p className="text-sm text-mute">Deleted {fmtDateTime(r.deleted_at)}</p></div>
            <div className="flex gap-2"><button className="btn btn-outline btn-sm" onClick={() => restore(r)}><RotateCcw className="h-3.5 w-3.5" />Restore</button><button className="btn btn-danger btn-sm" onClick={() => purge(r)}><Trash2 className="h-3.5 w-3.5" />Delete permanently</button></div></div>))}</div>
      )}
    </>
  );
}
