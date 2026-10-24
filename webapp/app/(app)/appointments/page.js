"use client";
import { AnimatePresence, motion } from "framer-motion";
import { CalendarClock, Check, ChevronLeft, ChevronRight, Inbox, Plus, Trash2, X } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { SlotPicker } from "@/components/DateTime";
import { Modal, useConfirm } from "@/components/Modal";
import { Badge, Empty, ErrorBox, Field, PageHeader, Skeleton, Tabs } from "@/components/ui";
import { del, patch, post } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { addDays, CLINICAL, dayKey, dayRange, fmtDateTime, fmtTime, useAct, useApi, useUrlState } from "@/lib/hooks";

const doctorLabel = (d) => `${d.full_name}${d.profile?.specialization ? ` · ${d.profile.specialization}` : ""}`;

function BookModal({ open, onClose, patientId, doctors, locations, defaultDoctor }) {
  const act = useAct();
  const patients = useApi(["patients", "all"], "/patients?limit=500", { enabled: open });
  const [doctor, setDoctor] = useState(defaultDoctor || "");
  const [day, setDay] = useState(dayKey());
  const [slot, setSlot] = useState("");
  const [repeat, setRepeat] = useState("none");
  useEffect(() => { if (open) { setSlot(""); setDay(dayKey()); setDoctor(defaultDoctor || ""); setRepeat("none"); } }, [open, defaultDoctor]);
  async function submit(e) {
    e.preventDefault();
    if (!slot) return;
    const f = Object.fromEntries(new FormData(e.currentTarget));
    const body = { patient_id: f.patient_id, scheduled_at: slot, reason: f.reason || null, doctor_id: doctor || null, location_id: f.location_id || null };
    if (repeat !== "none") { body.repeat_every_days = repeat === "weekly" ? 7 : 1; body.repeat_count = Number(f.count) || 4; }
    if (await act(() => post("/appointments", body), { ok: "Appointment booked", invalidate: ["appointments", "slots"] })) onClose();
  }
  return (
    <Modal open={open} onClose={onClose} title="Book appointment" wide>
      <form onSubmit={submit} className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Patient"><select name="patient_id" required defaultValue={patientId || ""} className="field"><option value="" disabled>Choose a patient</option>{(patients.data || []).map((p) => <option key={p.id} value={p.id}>{p.full_name}{p.phone ? ` · ${p.phone}` : ""}</option>)}</select></Field>
          <Field label="Doctor"><select value={doctor} onChange={(e) => { setDoctor(e.target.value); setSlot(""); }} className="field"><option value="">Any doctor</option>{doctors.map((d) => <option key={d.member_id} value={d.member_id}>{doctorLabel(d)}</option>)}</select></Field>
        </div>
        <div><p className="mb-2 text-sm font-medium">Day and time</p><SlotPicker doctorId={doctor} day={day} onDay={(d) => { setDay(d); setSlot(""); }} value={slot} onChange={setSlot} /></div>
        <div className="grid gap-4 sm:grid-cols-2">
          {locations.length > 0 && <Field label="Location"><select name="location_id" className="field"><option value="">Any</option>{locations.map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}</select></Field>}
          <Field label="Reason (optional)"><input name="reason" maxLength={200} className="field" /></Field>
          <Field label="Repeat"><select value={repeat} onChange={(e) => setRepeat(e.target.value)} className="field"><option value="none">Does not repeat</option><option value="weekly">Weekly</option><option value="daily">Daily</option></select></Field>
          {repeat !== "none" && <Field label="How many visits (2-12)"><input name="count" type="number" min={2} max={12} defaultValue={4} className="field" /></Field>}
        </div>
        <div className="flex items-center justify-between gap-3"><p className="text-sm text-mute">{slot ? `Selected: ${fmtDateTime(slot)}` : "Choose a time to continue."}</p>
          <div className="flex gap-3"><button type="button" className="btn btn-outline" onClick={onClose}>Cancel</button><button className="btn btn-primary" disabled={!slot}>Book</button></div></div>
      </form>
    </Modal>
  );
}

function ChangeTime({ appt, onClose, doctors }) {
  const act = useAct();
  const [day, setDay] = useState(dayKey(new Date(appt?.scheduled_at || Date.now())));
  const [slot, setSlot] = useState("");
  async function save() { if (await act(() => patch(`/appointments/${appt.id}`, { scheduled_at: slot, status: "confirmed" }), { ok: "Confirmed for the new time", invalidate: ["appointments", "slots"] })) onClose(); }
  return (
    <Modal open={!!appt} onClose={onClose} title="Offer a different time" wide>
      {appt && <div className="space-y-4"><p className="text-sm text-mute">{appt.patient_name} asked for {fmtDateTime(appt.scheduled_at)}. Choose a new time; the patient is told straight away.</p>
        <SlotPicker doctorId={appt.doctor_id || ""} day={day} onDay={(d) => { setDay(d); setSlot(""); }} value={slot} onChange={setSlot} />
        <div className="flex justify-end gap-3"><button className="btn btn-outline" onClick={onClose}>Cancel</button><button className="btn btn-primary" disabled={!slot} onClick={save}>Confirm new time</button></div></div>}
    </Modal>
  );
}

function Inner() {
  const { me } = useAuth();
  const params = useSearchParams();
  const pre = params.get("patient");
  const [tab, setTab] = useUrlState("tab", "schedule");
  const isDoctor = me.role === "doctor";
  const [day, setDay] = useState(dayKey());
  const [view, setView] = useState("day");
  const [doctor, setDoctor] = useState(isDoctor ? me.member_id : "");
  const [loc, setLoc] = useState("");
  const [open, setOpen] = useState(!!pre || params.get("new") === "1");
  const [change, setChange] = useState(null);
  const act = useAct();
  const confirm = useConfirm();
  const docs = useApi("doctors", "/doctors");
  const locs = useApi("locations", "/locations");
  const reqs = useApi(["appointments", "requests"], "/appointments/requests");
  const range = view === "day" ? dayRange(day) : (() => { const s0 = new Date(`${day}T00:00:00`); s0.setDate(s0.getDate() - ((s0.getDay() + 6) % 7)); const e0 = new Date(s0.getTime() + 7 * 864e5); return `start=${encodeURIComponent(s0.toISOString())}&end=${encodeURIComponent(e0.toISOString())}`; })();
  const list = useApi(["appointments", "day", view, day, doctor, loc], `/appointments?${range}${doctor ? `&doctor_id=${doctor}` : ""}${loc ? `&location_id=${loc}` : ""}`, { enabled: tab === "schedule" });
  const clinical = CLINICAL.includes(me.role);
  const set = (a, status, ok) => act(() => patch(`/appointments/${a.id}`, { status }), { ok, invalidate: ["appointments", "slots"] });
  const requests = (reqs.data || []).filter((r) => !isDoctor || !r.doctor_id || r.doctor_id === me.member_id);
  async function remove(a) {
    if (await confirm({ title: "Delete this appointment?", body: `${a.patient_name} · ${fmtTime(a.scheduled_at)}. It moves to Deleted history and can be restored by the owner.`, action: "Delete", danger: true }))
      act(() => del(`/appointments/${a.id}`), { ok: "Moved to Deleted history", invalidate: ["appointments", "slots"] });
  }
  async function decline(a) {
    if (await confirm({ title: "Decline this request?", body: `${a.patient_name} will be told the request was declined.`, action: "Decline", danger: true })) set(a, "cancelled", "Request declined");
  }
  const shift = (n) => setDay(addDays(day, n * (view === "week" ? 7 : 1)));
  return (
    <>
      <PageHeader title="Appointments" sub="Book visits, answer patient requests and move patients through the queue.">
        <button className="btn btn-primary" onClick={() => setOpen(true)}><Plus className="h-4 w-4" />Book appointment</button>
      </PageHeader>
      <Tabs tabs={[["schedule", "Schedule"], ["requests", `Patient requests${requests.length ? ` (${requests.length})` : ""}`]]} value={tab} onChange={setTab} />
      <ErrorBox error={list.error || reqs.error} />
      {tab === "requests" && (reqs.isLoading ? <Skeleton /> : requests.length === 0 ? <Empty icon={Inbox} title="No pending requests" hint="When a patient asks for an appointment, it appears here instantly." /> : (
        <ul className="space-y-3"><AnimatePresence initial={false}>{requests.map((a) => (
          <motion.li key={a.id} layout initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, x: -24 }} className="card flex flex-wrap items-center justify-between gap-3 border-l-4 border-l-warning px-5 py-4">
            <div><Link href={`/patients/${a.patient_id}`} className="font-semibold hover:text-brand">{a.patient_name}</Link><p className="text-sm text-mute">{fmtDateTime(a.scheduled_at)}{a.doctor_name ? ` · ${a.doctor_name}` : " · any doctor"}{a.reason ? ` · ${a.reason}` : ""}</p></div>
            <div className="flex flex-wrap gap-2"><button className="btn btn-primary btn-sm" onClick={() => set(a, "confirmed", "Appointment confirmed. The patient was told.")}><Check className="h-3.5 w-3.5" />Approve</button>
              <button className="btn btn-outline btn-sm" onClick={() => setChange(a)}>Other time</button><button className="btn btn-outline btn-sm" onClick={() => decline(a)}><X className="h-3.5 w-3.5" />Decline</button></div>
          </motion.li>))}</AnimatePresence></ul>))}
      {tab === "schedule" && (<>
        <div className="mb-5 flex flex-wrap items-center gap-2">
          <button className="btn btn-outline btn-sm" onClick={() => shift(-1)} aria-label="Previous"><ChevronLeft className="h-4 w-4" /></button>
          <label className="sr-only" htmlFor="day">Day</label><input id="day" type="date" value={day} onChange={(e) => e.target.value && setDay(e.target.value)} className="field w-auto" />
          <button className="btn btn-outline btn-sm" onClick={() => shift(1)} aria-label="Next"><ChevronRight className="h-4 w-4" /></button>
          <button className="btn btn-outline btn-sm" onClick={() => setDay(dayKey())}>Today</button>
          <select aria-label="View" value={view} onChange={(e) => setView(e.target.value)} className="field w-auto py-2"><option value="day">Day</option><option value="week">Week</option></select>
          <select aria-label="Doctor" value={doctor} onChange={(e) => setDoctor(e.target.value)} className="field w-auto py-2"><option value="">All doctors</option>{(docs.data || []).map((d) => <option key={d.member_id} value={d.member_id}>{d.full_name}</option>)}</select>
          {(locs.data || []).length > 0 && <select aria-label="Location" value={loc} onChange={(e) => setLoc(e.target.value)} className="field w-auto py-2"><option value="">All locations</option>{locs.data.map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}</select>}
        </div>
        {list.isLoading ? <Skeleton /> : list.data?.length === 0 ? (
          <Empty icon={CalendarClock} title="No appointments in this period" hint="Your schedule is clear."><button className="btn btn-primary" onClick={() => setOpen(true)}>Book appointment</button></Empty>
        ) : (
          <div className="space-y-3"><AnimatePresence initial={false}>
            {list.data.map((a) => (
              <motion.div key={a.id} layout initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, x: -24 }} className="card flex flex-wrap items-center justify-between gap-3 px-5 py-4">
                <div className="flex items-center gap-4"><span className={`font-mono text-sm text-mute ${view === "week" ? "w-28" : "w-14"}`}>{view === "week" ? `${new Date(a.scheduled_at).toLocaleDateString("en-GB", { weekday: "short", day: "numeric" })} ${fmtTime(a.scheduled_at)}` : fmtTime(a.scheduled_at)}</span>
                  <div><Link href={`/patients/${a.patient_id}`} className="font-semibold hover:text-brand">{a.patient_name}</Link><p className="text-xs text-mute">{[a.reason, a.doctor_name, a.queue_no ? `Queue #${a.queue_no}` : null].filter(Boolean).join(" · ") || "No details"}</p></div></div>
                <div className="flex flex-wrap items-center gap-2"><Badge s={a.status} />
                  {a.status === "requested" && <><button className="btn btn-primary btn-sm" onClick={() => set(a, "confirmed", "Appointment confirmed. The patient was told.")}>Approve</button><button className="btn btn-outline btn-sm" onClick={() => decline(a)}>Decline</button></>}
                  {["booked", "confirmed"].includes(a.status) && <>{a.status === "booked" && <button className="btn btn-outline btn-sm" onClick={() => set(a, "confirmed", "Appointment confirmed")}>Confirm</button>}<button className="btn btn-primary btn-sm" onClick={() => set(a, "arrived", `${a.patient_name} marked as arrived`)}>Arrived</button><button className="btn btn-outline btn-sm" onClick={() => set(a, "no_show", "Marked as no-show")}>No-show</button><button className="btn btn-outline btn-sm" onClick={() => set(a, "cancelled", "Appointment cancelled")}>Cancel</button></>}
                  {a.status === "arrived" && <>{clinical && <button className="btn btn-primary btn-sm" onClick={() => set(a, "in_consultation", "Consultation started")}>Call in</button>}<button className="btn btn-outline btn-sm" onClick={() => set(a, "cancelled", "Appointment cancelled")}>Cancel</button></>}
                  {a.status === "in_consultation" && <>{["owner", "doctor"].includes(me.role) && <Link href={`/consultations/new?patient=${a.patient_id}&appointment=${a.id}`} className="btn btn-outline btn-sm">Write notes</Link>}{clinical && <button className="btn btn-primary btn-sm" onClick={() => set(a, "completed", "Consultation completed")}>Complete</button>}</>}
                  {["cancelled", "no_show"].includes(a.status) && <button className="btn btn-outline btn-sm" onClick={() => set(a, "booked", "Rebooked")}>Rebook</button>}
                  {["owner", "receptionist"].includes(me.role) && <button onClick={() => remove(a)} aria-label="Delete appointment" className="rounded-lg p-2 text-mute hover:bg-danger/10 hover:text-danger-ink"><Trash2 className="h-4 w-4" /></button>}
                </div>
              </motion.div>))}
          </AnimatePresence></div>)}
      </>)}
      <BookModal open={open} onClose={() => setOpen(false)} patientId={pre} doctors={docs.data || []} locations={locs.data || []} defaultDoctor={isDoctor ? me.member_id : ""} />
      <ChangeTime appt={change} onClose={() => setChange(null)} doctors={docs.data || []} />
    </>
  );
}
export default function Appointments() { return <Suspense fallback={<Skeleton />}><Inner /></Suspense>; }
