"use client";
import { Plus, Printer, Sparkles, Trash2 } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { DateField } from "@/components/DateTime";
import { useConfirm } from "@/components/Modal";
import { ErrorBox, Field, PageHeader, Skeleton } from "@/components/ui";
import { del, openFile, patch, post } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { fmtDate, useAct, useApi } from "@/lib/hooks";

const VITALS = [["bp", "Blood pressure"], ["pulse", "Pulse"], ["temp", "Temperature"], ["spo2", "SpO₂"], ["weight", "Weight"]];
const blank = () => ({ medicine: "", dose: "", frequency: "", duration: "", instructions: "" });

function Form({ initial, patientId, appointmentId, patientName, id }) {
  const { me } = useAuth();
  const router = useRouter();
  const act = useAct();
  const confirm = useConfirm();
  const canEdit = ["owner", "doctor"].includes(me.role);
  const templates = useApi("templates", "/medicine-templates", { enabled: ["owner", "doctor"].includes(me.role) });
  const [rx, setRx] = useState(initial?.prescription?.length ? initial.prescription : []);
  const [busy, setBusy] = useState(false);
  const [follow, setFollow] = useState(initial?.follow_up_on || "");
  const setRow = (i, k, v) => setRx((l) => l.map((r, j) => (j === i ? { ...r, [k]: v } : r)));

  async function save(e) {
    e.preventDefault();
    const f = Object.fromEntries(new FormData(e.currentTarget));
    const vitals = Object.fromEntries(VITALS.map(([k]) => [k, (f[`v_${k}`] || "").trim()]).filter(([, v]) => v));
    const body = { complaint: f.complaint || null, examination: f.examination || null, assessment: f.assessment || null, plan: f.plan || null, vitals,
      prescription: rx.filter((r) => r.medicine.trim()), follow_up_on: follow || null, shared_with_patient: !!f.shared };
    setBusy(true);
    const r = await act(() => (id === "new" ? post("/consultations", { ...body, patient_id: patientId, appointment_id: appointmentId || null }) : patch(`/consultations/${id}`, body)),
      { ok: "Consultation saved", invalidate: ["consultations"] });
    setBusy(false);
    if (r && id === "new") router.replace(`/consultations/${r.id}`);
  }
  async function summarize() {
    await act(() => post(`/consultations/${id}/summarize`), { ok: "Draft summary created", invalidate: ["consultations"] });
  }
  async function remove() {
    if (await confirm({ title: "Delete this consultation?", body: "It moves to Deleted history, where the owner can restore it or remove it permanently.", action: "Delete", danger: true })) {
      if (await act(() => del(`/consultations/${id}`), { ok: "Moved to Deleted history", invalidate: ["consultations"] })) router.replace("/consultations");
    }
  }
  const ta = (name, label, rows = 3) => <Field label={label}><textarea name={name} rows={rows} defaultValue={initial?.[name] || ""} disabled={!canEdit} className="field" /></Field>;

  return (
    <>
      <PageHeader title={id === "new" ? "New consultation" : "Consultation"} sub={patientName}>
        {id !== "new" && <button className="btn btn-outline" onClick={() => act(() => openFile(`/consultations/${id}/prescription.pdf`))}>Open PDF</button>}
        {id !== "new" && <button className="btn btn-outline" onClick={() => window.print()}><Printer className="h-4 w-4" />Print</button>}
        {id !== "new" && canEdit && <button className="btn btn-outline" onClick={summarize}><Sparkles className="h-4 w-4" />AI draft summary</button>}
        {id !== "new" && canEdit && <button className="btn btn-outline text-danger-ink" onClick={remove}><Trash2 className="h-4 w-4" />Delete</button>}
      </PageHeader>
      {initial?.ai_summary && <div className="card mb-6 border-brand p-5"><p className="text-xs font-semibold text-brand">AI-generated draft. Review before relying on it.</p><p className="mt-2 whitespace-pre-wrap leading-7">{initial.ai_summary}</p></div>}
      <form key={initial ? initial.id + initial.created_at : "new"} onSubmit={save} className="space-y-6">
        <section className="card p-6"><h2 className="font-display text-lg font-bold">Vitals</h2>
          <div className="mt-4 grid grid-cols-2 gap-4 md:grid-cols-5">{VITALS.map(([k, l]) => <Field key={k} label={l}><input name={`v_${k}`} defaultValue={initial?.vitals?.[k] || ""} disabled={!canEdit} className="field" /></Field>)}</div></section>
        <section className="card grid gap-4 p-6 md:grid-cols-2">{ta("complaint", "Chief complaint")}{ta("examination", "Examination")}{ta("assessment", "Assessment")}{ta("plan", "Plan")}</section>
        <section className="card p-6"><div className="flex items-center justify-between"><h2 className="font-display text-lg font-bold">Prescription</h2>
          {canEdit && <div className="flex gap-2">{(templates.data || []).length > 0 && <select aria-label="Add from template" value="" onChange={(e) => { const t = templates.data.find((x) => x.id === e.target.value); if (t) setRx([...rx, { medicine: t.medicine, dose: t.dose, frequency: t.frequency, duration: t.duration, instructions: t.instructions }]); }} className="field w-auto py-1.5 text-sm"><option value="">From template…</option>{templates.data.map((t) => <option key={t.id} value={t.id}>{t.medicine} {t.dose}</option>)}</select>}<button type="button" className="btn btn-outline btn-sm" onClick={() => setRx([...rx, blank()])}><Plus className="h-4 w-4" />Add medicine</button></div>}</div>
          {rx.length === 0 && <p className="mt-3 text-sm text-mute">No medicines added.</p>}
          <div className="mt-4 space-y-3">{rx.map((r, i) => (
            <div key={i} className="grid gap-2 rounded-xl border border-line p-3 md:grid-cols-[1.6fr_1fr_1fr_1fr_auto]">
              {[["medicine", "Medicine"], ["dose", "Dose"], ["frequency", "Frequency"], ["duration", "Duration"]].map(([k, l]) => <input key={k} aria-label={l} placeholder={l} value={r[k]} disabled={!canEdit} onChange={(e) => setRow(i, k, e.target.value)} className="field" />)}
              {canEdit && <button type="button" aria-label="Remove medicine" onClick={() => setRx(rx.filter((_, j) => j !== i))} className="rounded-lg p-2 text-mute hover:bg-danger/10 hover:text-danger-ink"><Trash2 className="h-4 w-4" /></button>}
              <input aria-label="Instructions" placeholder="Instructions (optional)" value={r.instructions} disabled={!canEdit} onChange={(e) => setRow(i, "instructions", e.target.value)} className="field md:col-span-5" /></div>))}</div></section>
        <section className="card flex flex-wrap items-end gap-6 p-6"><Field label="Follow-up date"><div className="w-72"><DateField name="follow_up_on" label="Follow-up date" value={follow} onChange={canEdit ? setFollow : undefined} quick={[["3 days", 3], ["1 week", 7], ["2 weeks", 14], ["1 month", 30]]} /></div></Field>
          <label className="flex items-center gap-2 pb-3 text-sm"><input name="shared" type="checkbox" defaultChecked={initial ? initial.shared_with_patient : true} disabled={!canEdit} />Share prescription with the patient portal</label></section>
        {canEdit && <button className="btn btn-primary" disabled={busy}>{busy ? "Saving…" : "Save consultation"}</button>}
      </form>
      {initial && (
        <div className="print-only"><h1 style={{ fontSize: 24, fontWeight: 700 }}>{me.clinic.name}</h1><p>Prescription · {fmtDate(initial.created_at)}</p><hr style={{ margin: "12px 0" }} />
          <p><b>Patient:</b> {initial.patient_name}</p>{initial.assessment && <p><b>Assessment:</b> {initial.assessment}</p>}
          <table style={{ width: "100%", marginTop: 16, borderCollapse: "collapse" }}><thead><tr>{["Medicine", "Dose", "Frequency", "Duration", "Instructions"].map((h) => <th key={h} style={{ textAlign: "left", borderBottom: "1px solid #000", padding: 6 }}>{h}</th>)}</tr></thead>
            <tbody>{initial.prescription.map((r, i) => <tr key={i}>{[r.medicine, r.dose, r.frequency, r.duration, r.instructions].map((v, j) => <td key={j} style={{ padding: 6, borderBottom: "1px solid #ddd" }}>{v}</td>)}</tr>)}</tbody></table>
          {initial.follow_up_on && <p style={{ marginTop: 16 }}><b>Follow-up:</b> {fmtDate(initial.follow_up_on)}</p>}</div>
      )}
    </>
  );
}

function Inner() {
  const { id } = useParams();
  const sp = useSearchParams();
  const { me } = useAuth();
  const isNew = id === "new";
  const patientId = sp.get("patient");
  const existing = useApi(["consultations", "detail", id], `/consultations/${id}`, { enabled: !isNew });
  const pat = useApi(["patients", "detail", patientId], `/patients/${patientId}`, { enabled: isNew && !!patientId });
  if (isNew && !patientId) return <div className="card p-8"><p>Start a consultation from a patient's profile or from the queue.</p><Link href="/patients" className="btn btn-primary mt-4">Go to patients</Link></div>;
  if (isNew && !["owner", "doctor"].includes(me.role)) return <ErrorBox error={new Error("Only doctors can write consultations.")} />;
  if (existing.isLoading || pat.isLoading) return <Skeleton rows={6} />;
  if (existing.error || pat.error) return <ErrorBox error={existing.error || pat.error} />;
  return <Form id={id} initial={existing.data} patientId={patientId} appointmentId={sp.get("appointment")} patientName={existing.data?.patient_name || pat.data?.full_name} />;
}
export default function ConsultationPage() { return <Suspense fallback={<Skeleton rows={6} />}><Inner /></Suspense>; }
