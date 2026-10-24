"use client";
import { AnimatePresence, motion } from "framer-motion";
import { CalendarClock, Inbox } from "lucide-react";
import Link from "next/link";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Badge, Empty, ErrorBox, PageHeader, Skeleton, Stat } from "@/components/ui";
import { patch, post } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { dayKey, dayRange, firstName, fmtDateTime, fmtTime, money, tzOffset, useAct, useApi } from "@/lib/hooks";

const axis = { tick: { fill: "var(--muted)", fontSize: 12 }, axisLine: false, tickLine: false };
const greeting = () => { const h = new Date().getHours(); return h < 12 ? "morning" : h < 18 ? "afternoon" : "evening"; };

function RequestsCard() {
  const act = useAct();
  const q = useApi(["appointments", "requests"], "/appointments/requests");
  const list = q.data || [];
  if (!list.length) return null;
  const set = (a, status, ok) => act(() => patch(`/appointments/${a.id}`, { status }), { ok, invalidate: ["appointments", "slots"] });
  return (
    <section className="card mb-6 border-l-4 border-l-warning p-6">
      <div className="flex items-center justify-between"><h2 className="flex items-center gap-2 font-display text-xl font-bold"><Inbox className="h-5 w-5 text-warning-ink" aria-hidden="true" />Appointment requests ({list.length})</h2><Link href="/appointments?tab=requests" className="text-sm font-semibold text-brand">Open all</Link></div>
      <ul className="mt-4 space-y-2"><AnimatePresence initial={false}>{list.slice(0, 4).map((a) => (
        <motion.li key={a.id} layout initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, x: -20 }} className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-line px-4 py-3">
          <div><p className="font-semibold">{a.patient_name}</p><p className="text-xs text-mute">{fmtDateTime(a.scheduled_at)}{a.doctor_name ? ` · ${a.doctor_name}` : ""}</p></div>
          <div className="flex gap-2"><button className="btn btn-primary btn-sm" onClick={() => set(a, "confirmed", "Confirmed. The patient was told.")}>Approve</button><button className="btn btn-outline btn-sm" onClick={() => set(a, "cancelled", "Request declined")}>Decline</button></div></motion.li>))}</AnimatePresence></ul>
    </section>
  );
}

function QueueCard({ list, loading, title = "Live queue" }) {
  const queue = list.filter((a) => ["arrived", "in_consultation"].includes(a.status)).sort((a, b) => (a.queue_no || 0) - (b.queue_no || 0));
  return (
    <section className="card p-6"><h2 className="font-display text-xl font-bold">{title}</h2>
      <div className="mt-4 space-y-2">{loading ? <Skeleton rows={3} /> : queue.length === 0 ? <Empty icon={CalendarClock} title="The queue is clear" hint="Patients appear here when they arrive." /> : (
        <AnimatePresence initial={false}>{queue.map((a) => (
          <motion.div key={a.id} layout initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, x: -20 }} className="flex items-center justify-between rounded-xl border border-line px-4 py-3">
            <div className="flex items-center gap-3"><span className="font-mono text-sm text-mute">#{String(a.queue_no || 0).padStart(2, "0")}</span><div><p className="font-semibold">{a.patient_name}</p><p className="text-xs text-mute">{fmtTime(a.scheduled_at)}{a.doctor_name ? ` · ${a.doctor_name}` : ""}</p></div></div><Badge s={a.status} /></motion.div>))}</AnimatePresence>)}</div></section>
  );
}

function DoctorDashboard({ me }) {
  const act = useAct();
  const s = useApi("doctor-summary", "/doctor/summary", { refetchInterval: 60_000 });
  const today = dayKey();
  const appts = useApi(["appointments", "today", today], `/appointments?${dayRange(today)}&doctor_id=${me.member_id}`);
  const callNext = () => act(() => post("/appointments/queue/call-next"), { ok: "Next patient called in", invalidate: ["appointments", "doctor-summary"] });
  if (s.isLoading) return <Skeleton rows={4} />;
  if (s.error) return <ErrorBox error={s.error} />;
  const d = s.data;
  const reqs = Array.isArray(d.requests_for_me) ? d.requests_for_me.length : d.requests_for_me;
  return (
    <>
      <PageHeader title={`Good ${greeting()}, Dr. ${firstName(me.full_name)}`} sub={`${me.clinic.name} · your day at a glance`}>
        <button className="btn btn-primary" onClick={callNext} disabled={!d.today.waiting}>Call next patient</button><Link href="/appointments" className="btn btn-outline">My schedule</Link></PageHeader>
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4"><Stat label="My appointments today" value={d.today.mine} /><Stat label="Waiting for me" value={d.today.waiting} tone="text-warning-ink" /><Stat label="In consultation" value={d.today.in_consultation} tone="text-brand" /><Stat label="Completed" value={d.today.completed} tone="text-success-ink" /></div>
      <div className="mt-4 grid grid-cols-2 gap-4 lg:grid-cols-4"><Stat label="Patients seen (30 days)" value={d.patients_seen_30d} /><Stat label="Follow-ups due (7 days)" value={d.follow_ups_due_7d} /><Stat label="Requests for me" value={reqs || 0} tone={reqs ? "text-warning-ink" : ""} />
        <Stat label="Avg consultation" value={d.avg_consultation_minutes ?? 0} format={(v) => (d.avg_consultation_minutes == null ? "n/a" : `${v.toFixed(0)} min`)} /></div>
      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <QueueCard list={appts.data || []} loading={appts.isLoading} title="My queue" />
        <section className="card p-6"><h2 className="font-display text-xl font-bold">Coming up</h2><div className="mt-4 space-y-2">
          {d.upcoming.length === 0 ? <p className="text-mute">Nothing else booked for you.</p> : d.upcoming.map((u) => <Link key={u.id} href={`/patients/${u.patient_id}`} className="flex items-center justify-between rounded-xl border border-line px-4 py-3 hover:border-brand"><div><p className="font-semibold">{u.patient_name}</p><p className="text-xs text-mute">{fmtDateTime(u.scheduled_at)}{u.reason ? ` · ${u.reason}` : ""}</p></div><Badge s={u.status} /></Link>)}</div></section>
      </div>
      <section className="card mt-6 p-6"><h2 className="font-display text-xl font-bold">My visits, last 7 days</h2><div className="mt-4 h-52"><ResponsiveContainer width="100%" height="100%"><BarChart data={d.last7}><CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border)" /><XAxis dataKey="date" tickFormatter={(x) => x.slice(5)} {...axis} /><YAxis allowDecimals={false} width={30} {...axis} /><Tooltip /><Bar dataKey="visits" fill="var(--primary)" radius={[6, 6, 0, 0]} /></BarChart></ResponsiveContainer></div></section>
    </>
  );
}

export default function Dashboard() {
  const { me } = useAuth();
  const today = dayKey();
  const isDoctor = me.role === "doctor";
  const full = me.role === "owner";
  const appts = useApi(["appointments", "today", today], `/appointments?${dayRange(today)}`, { enabled: !isDoctor });
  const stats = useApi("analytics", `/analytics/summary?tz_offset_minutes=${tzOffset()}`, { enabled: full });
  if (isDoctor) return <DoctorDashboard me={me} />;
  const list = appts.data || [];
  const count = (s) => list.filter((a) => a.status === s).length;
  return (
    <>
      <PageHeader title={`Good ${greeting()}, ${firstName(me.full_name)}`} sub={me.clinic.name}><Link href="/appointments" className="btn btn-primary">Book appointment</Link></PageHeader>
      <ErrorBox error={appts.error} />
      {["owner", "receptionist"].includes(me.role) && <RequestsCard />}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4"><Stat label="Appointments today" value={list.length} /><Stat label="Waiting now" value={count("arrived")} tone="text-warning-ink" /><Stat label="In consultation" value={count("in_consultation")} tone="text-brand" /><Stat label="Completed" value={count("completed")} tone="text-success-ink" /></div>
      {full && stats.data && (<div className="mt-4 grid grid-cols-2 gap-4 lg:grid-cols-4"><Stat label="Pending invoices" value={stats.data.pending_invoices.count} tone={stats.data.pending_invoices.count ? "text-warning-ink" : ""} /><Stat label="Due to collect" value={stats.data.pending_invoices.due} format={(v) => money(Math.round(v))} /><Stat label="Follow-ups (7 days)" value={stats.data.follow_ups_due_7d} /><Stat label="New patients (30 days)" value={stats.data.new_patients_30d} /></div>)}
      <div className="mt-6 grid gap-6 lg:grid-cols-[1.1fr_1fr]">
        <QueueCard list={list} loading={appts.isLoading} />
        {full ? (
          <section className="card p-6"><h2 className="font-display text-xl font-bold">Revenue, last 7 days</h2><p className="mt-1 text-sm text-mute">Today {money(stats.data?.revenue.today)} · This month {money(stats.data?.revenue.month)}</p>
            <div className="mt-4 h-56">{stats.data ? <ResponsiveContainer width="100%" height="100%"><BarChart data={stats.data.last7}><CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border)" /><XAxis dataKey="date" tickFormatter={(d) => d.slice(5)} {...axis} /><YAxis width={48} {...axis} /><Tooltip formatter={(v) => money(v)} /><Bar dataKey="revenue" fill="var(--primary)" radius={[6, 6, 0, 0]} /></BarChart></ResponsiveContainer> : <Skeleton rows={3} />}</div></section>
        ) : <section className="card p-6"><h2 className="font-display text-xl font-bold">Next up</h2><div className="mt-4 space-y-2">
          {list.filter((a) => ["booked", "confirmed"].includes(a.status)).slice(0, 5).map((a) => <div key={a.id} className="flex justify-between rounded-xl border border-line px-4 py-3 text-sm"><span className="font-medium">{a.patient_name}</span><span className="text-mute">{fmtTime(a.scheduled_at)}</span></div>)}
          {list.filter((a) => ["booked", "confirmed"].includes(a.status)).length === 0 && <p className="text-mute">No more booked visits today.</p>}</div></section>}
      </div>
    </>
  );
}
