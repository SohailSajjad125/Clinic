"use client";
import { Plus, Search, Trash2, Users } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { DateField } from "@/components/DateTime";
import { Modal, useConfirm } from "@/components/Modal";
import { Empty, ErrorBox, Field, PageHeader, Skeleton } from "@/components/ui";
import { del, post } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { clean, fmtDate, useAct, useApi } from "@/lib/hooks";

function Inner() {
  const { me } = useAuth();
  const sp = useSearchParams();
  const [q, setQ] = useState("");
  const [dq, setDq] = useState("");
  const [open, setOpen] = useState(sp.get("new") === "1" && ["owner", "receptionist", "nurse"].includes(me.role));
  const act = useAct();
  const confirm = useConfirm();
  useEffect(() => { const t = setTimeout(() => setDq(q.trim()), 250); return () => clearTimeout(t); }, [q]);
  const list = useApi(["patients", "list", dq], `/patients?q=${encodeURIComponent(dq)}`);
  const canDelete = ["owner", "doctor"].includes(me.role);
  const canAdd = ["owner", "receptionist", "nurse"].includes(me.role);

  async function add(e) {
    e.preventDefault();
    const f = Object.fromEntries(new FormData(e.currentTarget));
    if (await act(() => post("/patients", clean(f)), { ok: "Patient added", invalidate: ["patients"] })) setOpen(false);
  }
  async function remove(p) {
    if (await confirm({ title: `Delete ${p.full_name}?`, body: "They'll move to Deleted history, where the clinic owner can restore them or remove them permanently.", action: "Delete", danger: true }))
      act(() => del(`/patients/${p.id}`), { ok: "Moved to Deleted history", invalidate: ["patients"] });
  }
  return (
    <>
      <PageHeader title="Patients" sub="Search, add and open patient records.">{canAdd && <button className="btn btn-primary" onClick={() => setOpen(true)}><Plus className="h-4 w-4" />Add patient</button>}</PageHeader>
      <div className="relative mb-5 max-w-md"><Search className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-mute" aria-hidden="true" />
        <label htmlFor="pq" className="sr-only">Search patients</label><input id="pq" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search by name, phone or email" className="field pl-10" /></div>
      <ErrorBox error={list.error} />
      {list.isLoading ? <Skeleton /> : list.data?.length === 0 ? (
        <Empty icon={Users} title={dq ? "No matching patients" : "No patients yet"} hint={dq ? "Try a different spelling or phone number." : "Add your first patient to get started."}>{!dq && canAdd && <button className="btn btn-primary" onClick={() => setOpen(true)}>Add patient</button>}</Empty>
      ) : (
        <div className="card overflow-x-auto"><table className="w-full min-w-[560px]"><thead className="border-b border-line"><tr><th className="th">Name</th><th className="th">Phone</th><th className="th">Gender</th><th className="th">Added</th><th className="th" /></tr></thead>
          <tbody className="divide-y divide-line">{list.data.map((p) => (
            <tr key={p.id} className="hover:bg-bg"><td className="td font-semibold"><Link href={`/patients/${p.id}`} className="hover:text-brand">{p.full_name}</Link></td><td className="td text-mute">{p.phone || "—"}</td>
              <td className="td capitalize text-mute">{p.gender || "—"}</td><td className="td text-mute">{fmtDate(p.created_at)}</td>
              <td className="td text-right">{canDelete && <button onClick={() => remove(p)} aria-label={`Delete ${p.full_name}`} className="rounded-lg p-2 text-mute hover:bg-danger/10 hover:text-danger-ink"><Trash2 className="h-4 w-4" /></button>}</td></tr>))}</tbody></table></div>
      )}
      <Modal open={open} onClose={() => setOpen(false)} title="Add patient" wide>
        <form onSubmit={add} className="grid gap-4 sm:grid-cols-2">
          <div className="sm:col-span-2"><Field label="Full name"><input name="full_name" required minLength={2} className="field" /></Field></div>
          <Field label="Phone"><input name="phone" type="tel" className="field" /></Field>
          <Field label="Email"><input name="email" type="email" className="field" /></Field>
          <Field label="Gender"><select name="gender" className="field"><option value="">Not set</option><option value="male">Male</option><option value="female">Female</option><option value="other">Other</option></select></Field>
          <Field label="Date of birth"><DateField name="date_of_birth" label="Date of birth" max={new Date().toISOString().slice(0, 10)} /></Field>
          <div className="sm:col-span-2"><Field label="Address"><input name="address" className="field" /></Field></div>
          <div className="sm:col-span-2"><Field label="Allergies"><input name="allergies" className="field" /></Field></div>
          <div className="sm:col-span-2"><Field label="Current medications"><input name="current_medications" className="field" /></Field></div>
          <Field label="Emergency contact"><input name="emergency_contact_name" className="field" /></Field><Field label="Emergency phone"><input name="emergency_contact_phone" type="tel" className="field" /></Field>
          <div className="flex justify-end gap-3 sm:col-span-2"><button type="button" className="btn btn-outline" onClick={() => setOpen(false)}>Cancel</button><button className="btn btn-primary">Save patient</button></div>
        </form>
      </Modal>
    </>
  );
}

export default function Patients() { return <Suspense fallback={<Skeleton />}><Inner /></Suspense>; }
