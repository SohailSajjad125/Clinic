"use client";
import { FileText, Upload } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { Suspense, useRef, useState } from "react";
import { DateField } from "@/components/DateTime";
import { Modal, useConfirm } from "@/components/Modal";
import { Badge, ErrorBox, Field, PageHeader, Skeleton, Tabs } from "@/components/ui";
import { del, openFile, patch, post, upload } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { BILLING, CLINICAL, fmtDate, fmtDateTime, money, useAct, useApi, useUrlState } from "@/lib/hooks";

const clean = (o) => Object.fromEntries(Object.entries(o).map(([k, v]) => [k, v === "" ? null : v]));

function Documents({ id }) {
  const act = useAct();
  const confirm = useConfirm();
  const input = useRef(null);
  const [category, setCategory] = useState("report");
  const [shared, setShared] = useState(false);
  const q = useApi(["documents", id], `/documents?patient_id=${id}`);
  async function pick(e) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    const fd = new FormData(); fd.append("file", file); fd.append("category", category); fd.append("shared", String(shared));
    act(() => upload(`/patients/${id}/documents`, fd), { ok: "Document uploaded", invalidate: ["documents"] });
  }
  async function remove(d) {
    if (await confirm({ title: `Delete ${d.filename}?`, body: "It moves to Deleted history, where the owner can restore it or erase it permanently.", action: "Delete", danger: true })) act(() => del(`/documents/${d.id}`), { ok: "Moved to Deleted history", invalidate: ["documents", "trash"] });
  }
  return (
    <section className="card p-6"><h2 className="font-display text-lg font-bold">Documents</h2>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <select aria-label="Category" value={category} onChange={(e) => setCategory(e.target.value)} className="field w-auto py-2"><option value="report">Report</option><option value="lab">Lab result</option><option value="scan">Scan</option><option value="other">Other</option></select>
        <label className="flex items-center gap-1.5 text-sm text-mute"><input type="checkbox" checked={shared} onChange={(e) => setShared(e.target.checked)} />Share with patient</label>
        <input ref={input} type="file" accept=".pdf,.png,.jpg,.jpeg,.webp,.txt" onChange={pick} className="hidden" aria-label="Choose file" />
        <button className="btn btn-outline btn-sm" onClick={() => input.current?.click()}><Upload className="h-3.5 w-3.5" />Upload</button></div>
      <p className="mt-1 text-xs text-mute">PDF, PNG, JPG, WebP or text, up to 10 MB.</p>
      <ul className="mt-3 divide-y divide-line">{(q.data || []).map((d) => (
        <li key={d.id} className="flex items-center justify-between gap-2 py-2.5 text-sm"><button onClick={() => act(() => openFile(`/documents/${d.id}/download`, { download: true, name: d.filename }))} className="flex min-w-0 items-center gap-2 text-left hover:text-brand"><FileText className="h-4 w-4 shrink-0" /><span className="truncate">{d.filename}</span></button>
          <span className="flex shrink-0 items-center gap-2 text-xs text-mute"><span className="capitalize">{d.category}</span>{d.shared_with_patient && <span className="rounded-full bg-accent-soft px-2 py-0.5 text-brand">Shared</span>}
            <button onClick={() => remove(d)} className="text-danger-ink hover:underline">Delete</button></span></li>))}</ul>
      {q.data?.length === 0 && <p className="mt-3 text-sm text-mute">No documents yet.</p>}
    </section>
  );
}

function Timeline({ id }) {
  const q = useApi(["patients", "timeline", id], `/patients/${id}/timeline`);
  return (
    <section className="card p-6"><h2 className="font-display text-lg font-bold">Timeline</h2>
      <ol className="mt-4 space-y-4 border-l border-line pl-5">{(q.data || []).slice(0, 25).map((i) => (
        <li key={`${i.type}-${i.id}`} className="relative"><span className="absolute -left-[26px] top-1.5 h-2.5 w-2.5 rounded-full bg-brand" /><p className="text-xs text-mute">{fmtDateTime(i.at)}</p><p className="font-medium">{i.title}</p>{i.detail && <p className="text-sm text-mute">{i.detail}</p>}</li>))}</ol>
      {q.data?.length === 0 && <p className="mt-3 text-sm text-mute">Nothing has happened yet.</p>}
    </section>
  );
}

function PortalAccess({ patient }) {
  const act = useAct();
  const confirm = useConfirm();
  const [open, setOpen] = useState(false);
  async function invite(e) {
    e.preventDefault();
    const f = Object.fromEntries(new FormData(e.currentTarget));
    if (await act(() => post(`/patients/${patient.id}/portal-access`, f), { ok: "Portal access created", invalidate: ["patients"] })) setOpen(false);
  }
  async function revoke() {
    if (await confirm({ title: "Remove portal access?", body: "The patient is signed out and can no longer log in. Their record is not affected.", action: "Remove access", danger: true })) act(() => del(`/patients/${patient.id}/portal-access`), { ok: "Portal access removed", invalidate: ["patients"] });
  }
  return (
    <section className="card p-6"><h2 className="font-display text-lg font-bold">Patient portal</h2>
      {patient.user_id ? (<><p className="mt-2 text-sm text-mute">This patient can sign in to view appointments, prescriptions, shared documents and invoices, and to message the clinic.</p><button className="btn btn-outline btn-sm mt-3" onClick={revoke}>Remove access</button></>) : (<>
        <p className="mt-2 text-sm text-mute">Give this patient a login for the portal.</p><button className="btn btn-outline btn-sm mt-3" onClick={() => setOpen(true)}>Create portal login</button></>)}
      <Modal open={open} onClose={() => setOpen(false)} title="Create portal login"><form onSubmit={invite} className="space-y-4">
        <Field label="Patient's email"><input name="email" type="email" required defaultValue={patient.email || ""} className="field" /></Field>
        <Field label="Temporary password" hint="At least 8 characters. Share it with the patient securely."><input name="password" required minLength={8} autoComplete="off" className="field" /></Field>
        <div className="flex justify-end gap-3"><button type="button" className="btn btn-outline" onClick={() => setOpen(false)}>Cancel</button><button className="btn btn-primary">Create</button></div></form></Modal>
    </section>
  );
}

function Inner() {
  const { id } = useParams();
  const { me } = useAuth();
  const act = useAct();
  const [tab, setTab] = useUrlState("tab", "profile");
  const p = useApi(["patients", "detail", id], `/patients/${id}`);
  const appts = useApi(["appointments", "patient", id], `/appointments?patient_id=${id}`);
  const invs = useApi(["invoices", "patient", id], `/invoices?patient_id=${id}`, { enabled: BILLING.includes(me.role) });
  if (p.isLoading) return <Skeleton rows={6} />;
  if (p.error) return <ErrorBox error={p.error} />;
  const d = p.data;
  async function save(e) {
    e.preventDefault();
    const f = Object.fromEntries(new FormData(e.currentTarget));
    if (!f.full_name?.trim()) return;
    act(() => patch(`/patients/${id}`, clean(f)), { ok: "Patient updated", invalidate: ["patients"] });
  }
  const F = (name, label, props = {}) => <Field label={label}><input name={name} defaultValue={d[name] || ""} className="field" {...props} /></Field>;
  return (
    <>
      <PageHeader title={d.full_name} sub={`Patient since ${fmtDate(d.created_at)}`}>
        <Link href={`/appointments?patient=${id}`} className="btn btn-outline">Book appointment</Link>
        {["owner", "doctor"].includes(me.role) && <Link href={`/consultations/new?patient=${id}`} className="btn btn-primary">New consultation</Link>}
        {["owner", "receptionist"].includes(me.role) && <Link href={`/billing?patient=${id}`} className="btn btn-outline">New invoice</Link>}
        {d.user_id && <Link href="/messages" className="btn btn-outline">Messages</Link>}
      </PageHeader>
      <Tabs tabs={[["profile", "Profile"], ["timeline", "Timeline"], ["documents", "Documents"], ["visits", "Visits & bills"]]} value={tab} onChange={setTab} />
      {tab === "profile" && (
        <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
          <form key={JSON.stringify(d)} onSubmit={save} className="card grid gap-4 p-6 sm:grid-cols-2">
            <div className="sm:col-span-2">{F("full_name", "Full name", { required: true, minLength: 2 })}</div>{F("phone", "Phone")}{F("email", "Email", { type: "email" })}
            <Field label="Gender"><select name="gender" defaultValue={d.gender || ""} className="field"><option value="">Not set</option><option value="male">Male</option><option value="female">Female</option><option value="other">Other</option></select></Field><Field label="Date of birth"><DateField name="date_of_birth" label="Date of birth" defaultValue={d.date_of_birth || ""} max={new Date().toISOString().slice(0, 10)} /></Field>
            <div className="sm:col-span-2">{F("address", "Address")}</div><div className="sm:col-span-2">{F("allergies", "Allergies")}</div><div className="sm:col-span-2">{F("current_medications", "Current medications")}</div>
            {F("emergency_contact_name", "Emergency contact")}{F("emergency_contact_phone", "Emergency phone", { type: "tel" })}
            <div className="sm:col-span-2"><Field label="Medical history"><textarea name="medical_history" rows={4} defaultValue={d.medical_history || ""} className="field" /></Field></div>
            <div className="sm:col-span-2"><button className="btn btn-primary">Save changes</button></div></form>
          {["owner", "doctor", "receptionist"].includes(me.role) && <PortalAccess patient={d} />}
        </div>)}
      {tab === "timeline" && <Timeline id={id} />}
      {tab === "documents" && <Documents id={id} />}
      {tab === "visits" && (
        <div className="grid gap-6 md:grid-cols-2">
          <section className="card p-6"><h2 className="font-display text-lg font-bold">Appointments</h2><div className="mt-3 space-y-2">{(appts.data || []).slice().reverse().slice(0, 12).map((a) => <div key={a.id} className="flex items-center justify-between text-sm"><span>{fmtDateTime(a.scheduled_at)}</span><Badge s={a.status} /></div>)}{appts.data?.length === 0 && <p className="text-sm text-mute">No appointments yet.</p>}</div></section>
          {BILLING.includes(me.role) && <section className="card p-6"><h2 className="font-display text-lg font-bold">Invoices</h2><div className="mt-3 space-y-2">{(invs.data || []).slice(0, 12).map((i) => <div key={i.id} className="flex items-center justify-between text-sm"><span>#{i.number} · {money(i.total)}</span><Badge s={i.status} /></div>)}{invs.data?.length === 0 && <p className="text-sm text-mute">No invoices yet.</p>}</div></section>}
        </div>)}
    </>
  );
}

export default function PatientPage() { return <Suspense fallback={<Skeleton rows={6} />}><Inner /></Suspense>; }
