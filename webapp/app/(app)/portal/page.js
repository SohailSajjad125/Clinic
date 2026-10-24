"use client";
import { CalendarClock, Eraser, FileText, Pill, Receipt, Send } from "lucide-react";
import { Suspense, useEffect, useRef, useState } from "react";
import { DoctorCard } from "@/components/Doctor";
import { SlotPicker } from "@/components/DateTime";
import { Dot, useDots, useSeen } from "@/lib/dots";
import { Modal, useConfirm } from "@/components/Modal";
import { Badge, Empty, ErrorBox, Field, PageHeader, Skeleton, Tabs } from "@/components/ui";
import { openFile, post } from "@/lib/api";
import { dayKey, fmtDate, fmtDateTime, money, useAct, useApi, useUrlState } from "@/lib/hooks";

const Section = ({ q, empty, children }) => q.isLoading ? <Skeleton rows={3} /> : q.error ? <ErrorBox error={q.error} /> : q.data.length === 0 ? empty : children(q.data);

function Overview({ go }) {
  const h = useApi("portal", "/portal/home");
  if (h.isLoading) return <Skeleton rows={3} />;
  if (h.error) return <ErrorBox error={h.error} />;
  const d = h.data;
  return (
    <div className="grid gap-4 md:grid-cols-3">
      <button onClick={() => go("appointments")} className="card p-6 text-left hover:border-brand"><p className="text-sm text-mute">Next appointment</p><p className="mt-2 font-display text-xl font-bold">{d.next_appointment ? fmtDateTime(d.next_appointment.scheduled_at) : "None booked"}</p></button>
      <button onClick={() => go("messages")} className="card p-6 text-left hover:border-brand"><p className="text-sm text-mute">Unread messages</p><p className="mt-2 font-display text-xl font-bold">{d.unread_messages}</p></button>
      <div className="card p-6"><p className="text-sm text-mute">Next follow-up</p><p className="mt-2 font-display text-xl font-bold">{d.next_follow_up ? fmtDate(d.next_follow_up) : "None due"}</p></div>
    </div>
  );
}

function Appointments() {
  const act = useAct();
  const confirm = useConfirm();
  const [open, setOpen] = useState(false);
  const [doctor, setDoctor] = useState(null);
  const [day, setDay] = useState(dayKey());
  const [slot, setSlot] = useState("");
  const q = useApi(["portal", "appointments"], "/portal/appointments");
  const docs = useApi(["portal", "doctors"], "/portal/doctors", { enabled: open });
  useEffect(() => { if (open) { setDoctor(null); setSlot(""); setDay(dayKey()); } }, [open]);
  async function book(e) {
    e.preventDefault();
    if (!slot) return;
    const f = Object.fromEntries(new FormData(e.currentTarget));
    if (await act(() => post("/portal/appointments", { scheduled_at: slot, doctor_id: doctor?.member_id || null, reason: f.reason || null }), { ok: "Request sent. The clinic will confirm shortly.", invalidate: ["portal", "slots"] })) setOpen(false);
  }
  async function cancel(a) {
    if (await confirm({ title: "Cancel this appointment?", body: fmtDateTime(a.scheduled_at), action: "Cancel appointment", danger: true })) act(() => post(`/portal/appointments/${a.id}/cancel`), { ok: "Appointment cancelled", invalidate: ["portal", "slots"] });
  }
  return (
    <>
      <div className="mb-4 flex justify-end"><button className="btn btn-primary" onClick={() => setOpen(true)}>Request an appointment</button></div>
      <Section q={q} empty={<Empty icon={CalendarClock} title="No appointments yet" hint="Request your first visit." />}>{(rows) => (
        <div className="card divide-y divide-line">{rows.map((a) => <div key={a.id} className="flex flex-wrap items-center justify-between gap-3 px-5 py-4"><div><p className="font-semibold">{fmtDateTime(a.scheduled_at)}</p><p className="text-sm text-mute">{[a.reason, a.doctor_name].filter(Boolean).join(" · ") || "Visit"}{a.status === "requested" ? " · waiting for the clinic to confirm" : ""}</p></div>
          <div className="flex items-center gap-3"><Badge s={a.status} />{["requested", "booked", "confirmed"].includes(a.status) && <button className="btn btn-outline btn-sm" onClick={() => cancel(a)}>Cancel</button>}</div></div>)}</div>)}</Section>
      <Modal open={open} onClose={() => setOpen(false)} title="Request an appointment" wide><form onSubmit={book} className="space-y-5">
        <div><p className="mb-2 text-sm font-medium">1. Choose a doctor <span className="font-normal text-mute">(optional)</span></p>
          <div className="grid max-h-64 gap-3 overflow-y-auto sm:grid-cols-2">{(docs.data || []).map((d) => <DoctorCard key={d.member_id} d={d} picked={doctor?.member_id === d.member_id} onPick={() => { setDoctor(doctor?.member_id === d.member_id ? null : d); setSlot(""); }} />)}</div>
          {docs.data?.length === 0 && <p className="text-sm text-mute">The clinic will assign a doctor.</p>}</div>
        <div><p className="mb-2 text-sm font-medium">2. Pick a day and time</p><SlotPicker endpoint="/portal/slots" doctorId={doctor?.member_id || ""} day={day} onDay={(d) => { setDay(d); setSlot(""); }} value={slot} onChange={setSlot} /></div>
        <Field label="3. What is it about? (optional)"><input name="reason" maxLength={200} className="field" /></Field>
        <div className="flex items-center justify-between gap-3"><p className="text-sm text-mute">{slot ? `Selected: ${fmtDateTime(slot)}` : "Choose a time to continue."}</p>
          <div className="flex gap-3"><button type="button" className="btn btn-outline" onClick={() => setOpen(false)}>Cancel</button><button className="btn btn-primary" disabled={!slot}>Send request</button></div></div>
      </form></Modal>
    </>
  );
}

function Prescriptions() {
  const act = useAct();
  const q = useApi(["portal", "rx"], "/portal/prescriptions");
  return <Section q={q} empty={<Empty icon={Pill} title="No prescriptions yet" hint="Prescriptions from your doctor appear here." />}>{(rows) => (
    <div className="space-y-4">{rows.map((r) => <div key={r.id} className="card p-6"><div className="flex flex-wrap items-center justify-between gap-2"><p className="font-semibold">{fmtDate(r.date)}{r.doctor ? ` · ${r.doctor}` : ""}</p>
      <button className="btn btn-outline btn-sm" onClick={() => act(() => openFile(`/portal/prescriptions/${r.id}/pdf`))}>Open PDF</button></div>
      <ul className="mt-3 space-y-1 text-sm">{r.prescription.map((m, i) => <li key={i}><b>{m.medicine}</b> <span className="text-mute">{[m.dose, m.frequency, m.duration].filter(Boolean).join(" · ")}</span></li>)}</ul>
      {r.follow_up_on && <p className="mt-3 text-sm text-mute">Follow-up: {fmtDate(r.follow_up_on)}</p>}</div>)}</div>)}</Section>;
}

function Documents() {
  const act = useAct();
  const q = useApi(["portal", "docs"], "/portal/documents");
  return <Section q={q} empty={<Empty icon={FileText} title="No documents yet" hint="Reports shared by the clinic appear here." />}>{(rows) => (
    <div className="card divide-y divide-line">{rows.map((d) => <div key={d.id} className="flex items-center justify-between gap-3 px-5 py-4"><div><p className="font-semibold">{d.filename}</p><p className="text-sm capitalize text-mute">{d.category} · {fmtDate(d.created_at)}</p></div>
      <button className="btn btn-outline btn-sm" onClick={() => act(() => openFile(`/portal/documents/${d.id}/download`, { download: true, name: d.filename }))}>Download</button></div>)}</div>)}</Section>;
}

function Invoices() {
  const act = useAct();
  const q = useApi(["portal", "invoices"], "/portal/invoices");
  return <Section q={q} empty={<Empty icon={Receipt} title="No invoices" />}>{(rows) => (
    <div className="card divide-y divide-line">{rows.map((i) => <div key={i.id} className="flex flex-wrap items-center justify-between gap-3 px-5 py-4"><div><p className="font-semibold">Invoice #{i.number}</p><p className="text-sm text-mute">{fmtDate(i.created_at)} · {money(i.paid)} of {money(i.total)} paid</p></div>
      <div className="flex items-center gap-3"><Badge s={i.status} /><button className="btn btn-outline btn-sm" onClick={() => act(() => openFile(`/portal/invoices/${i.id}/receipt.pdf`))}>Receipt</button></div></div>)}</div>)}</Section>;
}

function Messages() {
  const act = useAct();
  const confirm = useConfirm();
  const [text, setText] = useState("");
  const end = useRef(null);
  const q = useApi(["portal", "messages"], "/portal/messages", { staleTime: 0 });
  useEffect(() => { end.current?.scrollIntoView({ behavior: "smooth" }); }, [q.data?.length]);
  async function clearMine() {
    if (await confirm({ title: "Clear this chat?", body: "It disappears from your screen only. The clinic still has the conversation.", action: "Clear chat" }))
      act(() => post("/portal/messages/clear"), { ok: "Chat cleared from your view", invalidate: ["portal", "dots"] });
  }
  async function send(e) {
    e.preventDefault();
    const body = text.trim();
    if (!body) return;
    setText("");
    if (!(await act(() => post("/portal/messages", { body }), { invalidate: ["portal"] }))) setText(body);
  }
  return (
    <div className="card flex h-[60vh] flex-col"><div className="flex items-center justify-between border-b border-line px-5 py-3"><p className="font-semibold">Your clinic</p><button className="btn btn-outline btn-sm" disabled={!q.data?.length} onClick={clearMine}><Eraser className="h-3.5 w-3.5" />Clear chat</button></div><div className="flex-1 space-y-3 overflow-y-auto p-5">
      {q.data?.length === 0 && <p className="m-auto text-center text-mute">Write to your clinic here. Please don't use this for emergencies.</p>}
      {(q.data || []).map((m) => <div key={m.id} className={`flex ${m.from_patient ? "justify-end" : ""}`}><div className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm ${m.from_patient ? "bg-primary text-primary-fg" : "border border-line bg-bg"}`}>
        <p className={`text-xs ${m.from_patient ? "text-primary-fg opacity-75" : "text-mute"}`}>{m.from_patient ? "You" : m.sender_name} · {fmtDateTime(m.created_at)}</p><p className="whitespace-pre-wrap break-words leading-6">{m.body}</p></div></div>)}<div ref={end} /></div>
      <form onSubmit={send} className="flex gap-2 border-t border-line p-4"><label htmlFor="pm" className="sr-only">Message</label><input id="pm" value={text} onChange={(e) => setText(e.target.value)} maxLength={2000} placeholder="Write a message…" className="field" autoComplete="off" /><button className="btn btn-primary px-4" disabled={!text.trim()} aria-label="Send"><Send className="h-4 w-4" /></button></form></div>
  );
}

function Inner() {
  const [tab, setTab] = useUrlState("tab", "overview");
  const h = useApi("portal", "/portal/home");
  const seen = useSeen();
  const { dots } = useDots();
  useEffect(() => { if (dots[tab]) seen(tab); }, [tab, dots]); // eslint-disable-line react-hooks/exhaustive-deps
  return (
    <>
      <PageHeader title={h.data ? `Hello, ${h.data.name.split(" ")[0]}` : "My health"} sub={h.data?.clinic} />
      {tab === "overview" && <Overview go={setTab} />}{tab === "appointments" && <Appointments />}{tab === "prescriptions" && <Prescriptions />}
      {tab === "documents" && <Documents />}{tab === "invoices" && <Invoices />}{tab === "messages" && <Messages />}
    </>
  );
}
export default function Portal() { return <Suspense fallback={<Skeleton rows={4} />}><Inner /></Suspense>; }
