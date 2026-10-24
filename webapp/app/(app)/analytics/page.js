"use client";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { Area, AreaChart, Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ErrorBox, PageHeader, Skeleton, Stat } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { money, tzOffset, useApi } from "@/lib/hooks";

const axis = { tick: { fill: "var(--muted)", fontSize: 12 }, axisLine: false, tickLine: false };
const Chart = ({ title, children }) => <section className="card p-6"><h2 className="font-display text-lg font-bold">{title}</h2><div className="mt-4 h-60">{children}</div></section>;

export default function Analytics() {
  const { me } = useAuth();
  const router = useRouter();
  const ok = ["owner", "doctor"].includes(me.role);
  useEffect(() => { if (!ok) router.replace("/dashboard"); }, [ok, router]);
  const q = useApi("analytics", `/analytics/summary?tz_offset_minutes=${tzOffset()}`, { enabled: ok });
  if (q.isLoading) return <Skeleton rows={5} />;
  if (q.error) return <ErrorBox error={q.error} />;
  const d = q.data;
  const status = Object.entries(d.status_counts_30d).map(([k, v]) => ({ status: k.replace("_", " "), count: v }));
  return (
    <>
      <PageHeader title="Analytics" sub="How the clinic is running." />
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Stat label="Patients" value={d.patients_total} /><Stat label="New patients (30 days)" value={d.new_patients_30d} />
        <Stat label="Revenue this month" value={d.revenue.month} format={(v) => money(Math.round(v))} /><Stat label="No-show rate (30 days)" value={d.no_show_rate_30d * 100} format={(v) => `${v.toFixed(0)}%`} tone={d.no_show_rate_30d > 0.2 ? "text-danger-ink" : ""} />
      </div>
      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <Chart title="Revenue, last 7 days"><ResponsiveContainer width="100%" height="100%"><BarChart data={d.last7}><CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border)" /><XAxis dataKey="date" tickFormatter={(x) => x.slice(5)} {...axis} /><YAxis width={50} {...axis} /><Tooltip formatter={(v) => money(v)} /><Bar dataKey="revenue" fill="var(--primary)" radius={[6, 6, 0, 0]} /></BarChart></ResponsiveContainer></Chart>
        <Chart title="Appointments, last 7 days"><ResponsiveContainer width="100%" height="100%"><AreaChart data={d.last7}><CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border)" /><XAxis dataKey="date" tickFormatter={(x) => x.slice(5)} {...axis} /><YAxis allowDecimals={false} width={30} {...axis} /><Tooltip /><Area type="monotone" dataKey="appointments" stroke="var(--primary)" fill="color-mix(in srgb, var(--primary) 25%, transparent)" strokeWidth={2} /></AreaChart></ResponsiveContainer></Chart>
        <Chart title="Appointment outcomes, last 30 days">{status.length ? <ResponsiveContainer width="100%" height="100%"><BarChart data={status} layout="vertical"><CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="var(--border)" /><XAxis type="number" allowDecimals={false} {...axis} /><YAxis type="category" dataKey="status" width={110} {...axis} /><Tooltip /><Bar dataKey="count" fill="var(--accent)" radius={[0, 6, 6, 0]} /></BarChart></ResponsiveContainer> : <p className="text-mute">No appointments in the last 30 days.</p>}</Chart>
        <Chart title="Revenue by service, last 30 days">{d.revenue_by_service.length ? <ResponsiveContainer width="100%" height="100%"><BarChart data={d.revenue_by_service} layout="vertical"><CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="var(--border)" /><XAxis type="number" {...axis} /><YAxis type="category" dataKey="service" width={120} {...axis} /><Tooltip formatter={(v) => money(v)} /><Bar dataKey="amount" fill="var(--primary)" radius={[0, 6, 6, 0]} /></BarChart></ResponsiveContainer> : <p className="text-mute">No invoices in the last 30 days.</p>}</Chart>
        <section className="card p-6"><h2 className="font-display text-lg font-bold">Doctor utilisation, last 30 days</h2>
          <div className="mt-4 divide-y divide-line">{d.doctor_utilization.length === 0 && <p className="text-mute">No completed visits yet.</p>}{d.doctor_utilization.map((x) => <div key={x.doctor} className="flex justify-between py-2.5 text-sm"><span className="font-medium">{x.doctor}</span><span className="text-mute">{x.visits} visits · {x.minutes} min</span></div>)}</div></section>
        <section className="card p-6"><h2 className="font-display text-lg font-bold">Patients</h2><dl className="mt-4 grid grid-cols-2 gap-4 text-sm">
          {[["New patients seen (30 days)", d.patient_mix_30d.new], ["Returning patients seen", d.patient_mix_30d.returning], ["Avg consultation", d.avg_consultation_minutes != null ? `${d.avg_consultation_minutes} min` : "n/a"], ["Retention (90 days)", d.retention_90d != null ? `${Math.round(d.retention_90d * 100)}%` : "n/a"], ["Cancellation rate", `${Math.round(d.cancellation_rate_30d * 100)}%`], ["Pending invoices", `${d.pending_invoices.count} · ${money(d.pending_invoices.due)}`]].map(([k, v]) => <div key={k}><dt className="text-mute">{k}</dt><dd className="font-display text-lg font-bold">{v}</dd></div>)}</dl></section>
        <section className="card p-6"><h2 className="font-display text-lg font-bold">Today</h2><dl className="mt-4 grid grid-cols-2 gap-4 text-sm">
          {[["Appointments", d.today.appointments], ["Waiting", d.today.waiting], ["In consultation", d.today.in_consultation], ["Completed", d.today.completed], ["Revenue today", money(d.revenue.today)], ["Last 30 days", money(d.revenue.last_30d)]].map(([k, v]) => <div key={k}><dt className="text-mute">{k}</dt><dd className="font-display text-xl font-bold">{v}</dd></div>)}</dl></section>
      </div>
    </>
  );
}
