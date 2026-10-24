"use client";
import { AnimatePresence, motion } from "framer-motion";
import { Activity, PhoneCall, UserPlus } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { Modal } from "@/components/Modal";
import { Badge, Empty, ErrorBox, Field, PageHeader, Skeleton } from "@/components/ui";
import { patch, post } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { CLINICAL, dayKey, dayRange, fmtTime, useAct, useApi } from "@/lib/hooks";

export default function Queue() {
  const { me } = useAuth();
  const act = useAct();
  const [open, setOpen] = useState(false);
  const today = dayKey();
  const list = useApi(["appointments", "queue", today], `/appointments?${dayRange(today)}`, { refetchInterval: 30_000 });
  const patients = useApi(["patients", "all"], "/patients?limit=500", { enabled: open });
  const staff = useApi("staff", "/staff", { enabled: open });
  const clinical = CLINICAL.includes(me.role);
  const all = list.data || [];
  const waiting = all.filter((a) => a.status === "arrived").sort((a, b) => (a.queue_no || 0) - (b.queue_no || 0));
  const inside = all.filter((a) => a.status === "in_consultation");
  const upcoming = all.filter((a) => ["booked", "confirmed"].includes(a.status));
  const set = (a, status, ok) => act(() => patch(`/appointments/${a.id}`, { status }), { ok, invalidate: ["appointments"] });

  async function walkIn(e) {
    e.preventDefault();
    const f = Object.fromEntries(new FormData(e.currentTarget));
    if (await act(() => post("/appointments/walk-in", { patient_id: f.patient_id, doctor_id: f.doctor_id || null, reason: f.reason || null }), { ok: "Walk-in added to the queue", invalidate: ["appointments"] })) setOpen(false);
  }
  const callNext = () => act(() => post("/appointments/queue/call-next"), { ok: "Next patient called in", invalidate: ["appointments"] });
  const Row = ({ a, children }) => (
    <motion.li layout initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, x: -20 }} className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-line bg-surface px-4 py-3">
      <div className="flex items-center gap-3"><span className="w-10 font-mono text-sm text-mute">{a.queue_no ? `#${String(a.queue_no).padStart(2, "0")}` : fmtTime(a.scheduled_at)}</span>
        <div><Link href={`/patients/${a.patient_id}`} className="font-semibold hover:text-brand">{a.patient_name}</Link><p className="text-xs text-mute">{[a.is_walk_in && "Walk-in", a.reason, a.doctor_name].filter(Boolean).join(" · ")}</p></div></div>
      <div className="flex items-center gap-2"><Badge s={a.status} />{children}</div>
    </motion.li>
  );
  return (
    <>
      <PageHeader title="Live queue" sub="Updates instantly on every screen.">
        <button className="btn btn-outline" onClick={() => setOpen(true)}><UserPlus className="h-4 w-4" />Add walk-in</button>
        {clinical && <button className="btn btn-primary" onClick={callNext} disabled={!waiting.length}><PhoneCall className="h-4 w-4" />Call next</button>}
      </PageHeader>
      <ErrorBox error={list.error} />
      {list.isLoading ? <Skeleton /> : (
        <div className="grid gap-6 lg:grid-cols-2">
          <section><h2 className="mb-3 font-display text-lg font-bold">Waiting ({waiting.length})</h2>
            {waiting.length === 0 ? <Empty icon={Activity} title="Nobody is waiting" hint="Patients appear here when marked as arrived." /> : <ul className="space-y-2"><AnimatePresence initial={false}>{waiting.map((a) => <Row key={a.id} a={a}>{clinical && <button className="btn btn-primary btn-sm" onClick={() => set(a, "in_consultation", "Consultation started")}>Call in</button>}</Row>)}</AnimatePresence></ul>}</section>
          <section className="space-y-6">
            <div><h2 className="mb-3 font-display text-lg font-bold">In consultation ({inside.length})</h2>
              <ul className="space-y-2"><AnimatePresence initial={false}>{inside.map((a) => <Row key={a.id} a={a}>{["owner", "doctor"].includes(me.role) && <Link className="btn btn-outline btn-sm" href={`/consultations/new?patient=${a.patient_id}&appointment=${a.id}`}>Notes</Link>}{clinical && <button className="btn btn-primary btn-sm" onClick={() => set(a, "completed", "Consultation completed")}>Complete</button>}</Row>)}</AnimatePresence></ul>
              {inside.length === 0 && <p className="text-sm text-mute">No one is with a doctor right now.</p>}</div>
            <div><h2 className="mb-3 font-display text-lg font-bold">Expected today ({upcoming.length})</h2>
              <ul className="space-y-2">{upcoming.map((a) => <Row key={a.id} a={a}><button className="btn btn-outline btn-sm" onClick={() => set(a, "arrived", `${a.patient_name} marked as arrived`)}>Arrived</button></Row>)}</ul>
              {upcoming.length === 0 && <p className="text-sm text-mute">No more booked visits today.</p>}</div>
          </section>
        </div>)}
      <Modal open={open} onClose={() => setOpen(false)} title="Add walk-in patient">
        <form onSubmit={walkIn} className="space-y-4">
          <Field label="Patient"><select name="patient_id" required defaultValue="" className="field"><option value="" disabled>Choose a patient</option>{(patients.data || []).map((p) => <option key={p.id} value={p.id}>{p.full_name}{p.phone ? ` · ${p.phone}` : ""}</option>)}</select></Field>
          <Field label="Doctor"><select name="doctor_id" className="field"><option value="">Any doctor</option>{(staff.data || []).filter((s) => ["doctor", "owner"].includes(s.role)).map((d) => <option key={d.member_id} value={d.member_id}>{d.full_name}</option>)}</select></Field>
          <Field label="Reason (optional)"><input name="reason" maxLength={200} className="field" /></Field>
          <div className="flex justify-end gap-3"><button type="button" className="btn btn-outline" onClick={() => setOpen(false)}>Cancel</button><button className="btn btn-primary">Add to queue</button></div>
        </form>
      </Modal>
    </>
  );
}
