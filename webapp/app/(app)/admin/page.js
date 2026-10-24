"use client";
import { Eye, EyeOff, KeyRound } from "lucide-react";
import { Suspense, useEffect, useState } from "react";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Modal, useConfirm } from "@/components/Modal";
import { Badge, Counter, ErrorBox, Field, PageHeader, Skeleton, Stat, Tabs } from "@/components/ui";
import { api, patch, post } from "@/lib/api";
import { Dot, useDots, useSeen } from "@/lib/dots";
import { fmtDate, fmtDateTime, useAct, useApi, useUrlState } from "@/lib/hooks";

const PLANS = ["starter", "clinic", "group", "enterprise"];
const axis = { tick: { fill: "var(--muted)", fontSize: 12 }, axisLine: false, tickLine: false };
const ago = (d) => (d ? fmtDateTime(d) : "never");

function Overview() {
  const q = useApi(["admin", "stats"], "/admin/stats");
  const su = useApi(["admin", "signups"], "/admin/signups");
  if (q.isLoading) return <Skeleton rows={3} />;
  if (q.error) return <ErrorBox error={q.error} />;
  const d = q.data;
  return (
    <>
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4"><Stat label="Clinics" value={d.clinics} /><Stat label="New clinics (30 days)" value={d.new_clinics_30d} /><Stat label="Patients" value={d.patients} /><Stat label="Appointments (30 days)" value={d.appointments_30d} /></div>
      <div className="mt-4 grid grid-cols-2 gap-4 lg:grid-cols-4"><Stat label="Users" value={d.users} /><Stat label="Active clinics" value={d.active_clinics} /><Stat label="Unhandled messages" value={d.unhandled_messages} tone={d.unhandled_messages ? "text-warning-ink" : ""} /></div>
      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <section className="card p-6"><h2 className="font-display text-lg font-bold">Clinics by plan</h2><div className="mt-3 grid grid-cols-2 gap-4">{PLANS.map((p) => <div key={p}><p className="text-sm capitalize text-mute">{p}</p><p className="font-display text-2xl font-bold"><Counter value={d.plans[p] || 0} /></p></div>)}</div></section>
        <section className="card p-6"><h2 className="font-display text-lg font-bold">Sign-ups, last 14 days</h2><div className="mt-3 h-44">{su.data && <ResponsiveContainer width="100%" height="100%"><AreaChart data={su.data}><CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border)" /><XAxis dataKey="date" tickFormatter={(x) => x.slice(5)} {...axis} /><YAxis allowDecimals={false} width={28} {...axis} /><Tooltip /><Area type="monotone" dataKey="patients" stroke="var(--accent)" fill="color-mix(in srgb, var(--accent) 25%, transparent)" /><Area type="monotone" dataKey="clinics" stroke="var(--primary)" fill="color-mix(in srgb, var(--primary) 35%, transparent)" /></AreaChart></ResponsiveContainer>}</div><p className="mt-2 text-xs text-mute">Strong gold: clinics · soft gold: patients</p></section>
      </div>
    </>
  );
}

function Clinics() {
  const act = useAct();
  const confirm = useConfirm();
  const [open, setOpen] = useState(null);
  const q = useApi(["admin", "clinics"], "/admin/clinics");
  const det = useApi(["admin", "clinic", open], `/admin/clinics/${open}`, { enabled: !!open });
  const upd = (c, body, ok) => act(() => patch(`/admin/clinics/${c.id}`, body), { ok, invalidate: ["admin"] });
  async function toggle(c) {
    const suspend = c.status === "active";
    if (!suspend || await confirm({ title: `Suspend ${c.name}?`, body: "Everyone in this clinic is signed out and can't sign in until you reactivate it.", action: "Suspend", danger: true })) upd(c, { status: suspend ? "suspended" : "active" }, suspend ? "Clinic suspended" : "Clinic reactivated");
  }
  if (q.isLoading) return <Skeleton />;
  return (
    <>
      <div className="card overflow-x-auto"><table className="w-full min-w-[760px]"><thead className="border-b border-line"><tr><th className="th">Clinic</th><th className="th">Owner</th><th className="th">Patients</th><th className="th">Team</th><th className="th">Plan</th><th className="th">Status</th><th className="th" /></tr></thead>
        <tbody className="divide-y divide-line">{q.data.map((c) => <tr key={c.id}><td className="td"><button className="text-left font-semibold hover:text-brand" onClick={() => setOpen(c.id)}>{c.name}</button><p className="text-xs text-mute">{c.city} · since {fmtDate(c.created_at)}</p></td><td className="td text-mute">{c.owner_email}</td><td className="td">{c.patients}</td><td className="td">{c.team}</td>
          <td className="td"><select aria-label={`Plan for ${c.name}`} value={c.plan} onChange={(e) => upd(c, { plan: e.target.value }, "Plan updated")} className="field py-1.5">{PLANS.map((p) => <option key={p}>{p}</option>)}</select></td>
          <td className="td"><Badge s={c.status === "active" ? "completed" : "cancelled"} /></td><td className="td text-right"><button className="btn btn-outline btn-sm" onClick={() => toggle(c)}>{c.status === "active" ? "Suspend" : "Reactivate"}</button></td></tr>)}</tbody></table></div>
      <Modal open={!!open} onClose={() => setOpen(null)} title={det.data?.name || "Clinic"} wide>
        {det.isLoading ? <Skeleton rows={3} /> : det.data && (<div className="space-y-4">
          <p className="text-sm text-mute">{det.data.clinic_type} · {det.data.city}, {det.data.country} · plan <b className="capitalize text-ink">{det.data.plan}</b> · {det.data.public_listing ? "listed for patient sign-up" : "hidden from patient sign-up"}</p>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">{Object.entries(det.data.counts).map(([k, v]) => <div key={k} className="rounded-xl border border-line p-3"><p className="text-xs capitalize text-mute">{k.replaceAll("_", " ")}</p><p className="font-display text-xl font-bold">{v}</p></div>)}</div>
          <div><p className="mb-2 text-sm font-semibold">Team</p><ul className="divide-y divide-line rounded-xl border border-line">{det.data.team.map((m) => <li key={m.user_id} className="flex items-center justify-between px-4 py-2.5 text-sm"><span><b>{m.name}</b> <span className="text-mute">{m.email}</span></span><span className="text-xs text-mute"><span className="capitalize">{m.role}</span> · last login {ago(m.last_login)}</span></li>)}</ul></div>
        </div>)}
      </Modal>
    </>
  );
}

function Users() {
  const act = useAct();
  const confirm = useConfirm();
  const [q, setQ] = useState("");
  const [dq, setDq] = useState("");
  useEffect(() => { const t = setTimeout(() => setDq(q.trim()), 250); return () => clearTimeout(t); }, [q]);
  const list = useApi(["admin", "users", dq], `/admin/users?q=${encodeURIComponent(dq)}`);
  async function toggle(u) {
    if (!u.is_active || await confirm({ title: `Disable ${u.name}?`, body: "They are signed out everywhere and can't log in until re-enabled.", action: "Disable", danger: true })) act(() => patch(`/admin/users/${u.id}`, { is_active: !u.is_active }), { ok: u.is_active ? "User disabled" : "User enabled", invalidate: ["admin"] });
  }
  return (
    <>
      <label className="sr-only" htmlFor="uq">Search users</label><input id="uq" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search by name or email" className="field mb-4 max-w-md" />
      {list.isLoading ? <Skeleton /> : (
        <div className="card overflow-x-auto"><table className="w-full min-w-[720px]"><thead className="border-b border-line"><tr><th className="th">User</th><th className="th">Clinics and roles</th><th className="th">Last login</th><th className="th">Sessions</th><th className="th" /></tr></thead>
          <tbody className="divide-y divide-line">{list.data.map((u) => <tr key={u.id}><td className="td"><p className="font-semibold">{u.name}{!u.is_active && <span className="ml-2 text-xs text-danger-ink">disabled</span>}{u.is_superadmin && <span className="ml-2 text-xs text-brand">platform admin</span>}</p><p className="text-xs text-mute">{u.email}</p></td>
            <td className="td text-sm text-mute">{u.memberships.map((m) => `${m.clinic} (${m.role})`).join(", ") || "-"}</td><td className="td text-mute">{ago(u.last_login)}</td><td className="td">{u.sessions}</td>
            <td className="td text-right">{!u.is_superadmin && <button className="btn btn-outline btn-sm" onClick={() => toggle(u)}>{u.is_active ? "Disable" : "Enable"}</button>}</td></tr>)}</tbody></table></div>)}
    </>
  );
}

function Audit() {
  const [f, setF] = useState({ action: "", clinic_id: "" });
  const clinics = useApi(["admin", "clinics"], "/admin/clinics");
  const qs = new URLSearchParams({ limit: "200", ...(f.action && { action: f.action }), ...(f.clinic_id && { clinic_id: f.clinic_id }) }).toString();
  const list = useApi(["admin", "audit", qs], `/admin/audit?${qs}`);
  return (
    <>
      <div className="mb-4 flex flex-wrap gap-3">
        <input aria-label="Filter by action" value={f.action} onChange={(e) => setF({ ...f, action: e.target.value })} placeholder="Action contains… e.g. deleted" className="field max-w-xs" />
        <select aria-label="Clinic" value={f.clinic_id} onChange={(e) => setF({ ...f, clinic_id: e.target.value })} className="field max-w-xs"><option value="">All clinics</option>{(clinics.data || []).map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</select></div>
      {list.isLoading ? <Skeleton /> : (
        <div className="card overflow-x-auto"><table className="w-full min-w-[760px]"><thead className="border-b border-line"><tr><th className="th">When</th><th className="th">Clinic</th><th className="th">Who</th><th className="th">Action</th><th className="th">Record</th></tr></thead>
          <tbody className="divide-y divide-line">{list.data.map((e) => <tr key={e.id}><td className="td whitespace-nowrap text-mute">{fmtDateTime(e.at)}</td><td className="td">{e.clinic || <span className="text-mute">Platform</span>}</td><td className="td">{e.actor}<p className="text-xs text-mute">{e.actor_email}</p></td><td className="td font-mono text-xs">{e.action}</td><td className="td font-mono text-xs text-mute">{e.entity}{e.entity_id ? ` · ${String(e.entity_id).slice(0, 8)}` : ""}</td></tr>)}</tbody></table>
          {list.data.length === 0 && <p className="p-6 text-mute">No matching entries.</p>}</div>)}
    </>
  );
}

function Support() {
  const act = useAct();
  const q = useApi(["admin", "messages"], "/admin/messages");
  if (q.isLoading) return <Skeleton />;
  return (
    <div className="space-y-3">{q.data.length === 0 && <p className="text-mute">No messages yet.</p>}{q.data.map((m) => (
      <div key={m.id} className={`card p-5 ${m.handled ? "opacity-60" : ""}`}><div className="flex flex-wrap items-center justify-between gap-2"><p className="font-semibold">{m.name} <span className="font-normal text-mute">· {m.email}{m.phone ? ` · ${m.phone}` : ""}</span></p><span className="text-xs text-mute">{fmtDateTime(m.created_at)} · {m.topic}</span></div>
        {m.clinic_name && <p className="text-sm text-mute">{m.clinic_name}</p>}<p className="mt-2 whitespace-pre-wrap leading-7">{m.message}</p>
        {!m.handled && <button className="btn btn-outline btn-sm mt-3" onClick={() => act(() => post(`/admin/messages/${m.id}/handled`), { ok: "Marked as handled", invalidate: ["admin"] })}>Mark handled</button>}</div>))}</div>
  );
}

function Messaging() {
  const [st, setSt] = useState("");
  const q = useApi(["admin", "outbound", st], `/admin/outbound${st ? `?status=${st}` : ""}`);
  return (
    <>
      <select aria-label="Status" value={st} onChange={(e) => setSt(e.target.value)} className="field mb-4 max-w-xs"><option value="">All</option><option value="sent">Sent</option><option value="failed">Failed</option><option value="skipped">Skipped (channel not set up)</option></select>
      {q.isLoading ? <Skeleton /> : <div className="card overflow-x-auto"><table className="w-full min-w-[640px]"><thead className="border-b border-line"><tr><th className="th">When</th><th className="th">Clinic</th><th className="th">Channel</th><th className="th">Subject</th><th className="th">Result</th></tr></thead>
        <tbody className="divide-y divide-line">{q.data.map((m) => <tr key={m.id}><td className="td whitespace-nowrap text-mute">{fmtDateTime(m.at)}</td><td className="td">{m.clinic}</td><td className="td capitalize">{m.channel}</td><td className="td">{m.subject}</td><td className="td"><span className={m.status === "failed" ? "text-danger-ink" : m.status === "sent" ? "text-success-ink" : "text-mute"}>{m.status}</span>{m.error && <p className="max-w-[240px] truncate text-xs text-mute" title={m.error}>{m.error}</p>}</td></tr>)}</tbody></table>
        {q.data.length === 0 && <p className="p-6 text-mute">Nothing logged yet.</p>}</div>}
    </>
  );
}

function Health() {
  const q = useApi(["admin", "health"], "/admin/health", { refetchInterval: 15_000 });
  if (q.isLoading) return <Skeleton rows={3} />;
  const d = q.data;
  const row = (label, ok, note) => <div key={label} className="flex items-center justify-between py-3"><span>{label}</span><span className={`text-sm font-semibold ${ok ? "text-success-ink" : "text-warning-ink"}`}>{note ?? (ok ? "OK" : "Not configured")}</span></div>;
  return (
    <div className="card max-w-xl divide-y divide-line px-6">{row("Database", d.database)}{row("Reminder scheduler", d.scheduler_enabled, d.scheduler_enabled ? "Running" : "Disabled")}{row("Email (SMTP)", d.email_configured)}{row("SMS (Twilio)", d.sms_configured)}{row("WhatsApp (Twilio)", d.whatsapp_configured)}
      {row("AI assistant (Groq)", d.assistant_configured)}{row("Live connections", true, String(d.websocket_connections))}{row("Messages sent / failed (24h)", d.messages_failed_24h === 0, `${d.messages_sent_24h} / ${d.messages_failed_24h}`)}</div>
  );
}

const GROUPS = { assistant: "AI assistant (Groq)", email: "Email", sms: "SMS and WhatsApp (Twilio)", platform: "Platform switches" };

function SettingField({ s, draft, setDraft, clear, setClear }) {
  const [show, setShow] = useState(false);
  const on = (v) => setDraft({ ...draft, [s.name]: v });
  if (s.kind === "bool") return <label className="flex items-center gap-3 py-2"><input type="checkbox" checked={draft[s.name] ?? s.value} onChange={(e) => on(e.target.checked)} /><span>{s.label}</span></label>;
  if (s.secret) return (
    <Field label={s.label} hint={s.is_set ? `A key is saved (${s.hint}). Leave blank to keep it, type a new one to replace it.` : "No key saved yet."}>
      <div className="flex gap-2"><div className="relative flex-1"><KeyRound className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-mute" aria-hidden="true" /><input type={show ? "text" : "password"} autoComplete="off" value={draft[s.name] ?? ""} onChange={(e) => on(e.target.value)} placeholder={s.is_set ? "••••••••••••" : "Paste the key"} className="field pl-10" /></div>
        <button type="button" className="btn btn-outline btn-sm" aria-label={show ? "Hide" : "Show"} onClick={() => setShow(!show)}>{show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}</button>
        {s.is_set && <label className="flex items-center gap-1.5 text-xs text-danger-ink"><input type="checkbox" checked={clear.includes(s.name)} onChange={(e) => setClear(e.target.checked ? [...clear, s.name] : clear.filter((x) => x !== s.name))} />Remove</label>}</div></Field>);
  return <Field label={s.label} hint={`Source: ${s.source}`}><input value={draft[s.name] ?? s.value ?? ""} onChange={(e) => on(e.target.value)} type={s.kind === "int" ? "number" : "text"} className="field" /></Field>;
}

function Settings() {
  const act = useAct();
  const q = useApi(["admin", "settings"], "/admin/settings");
  const [draft, setDraft] = useState({});
  const [clear, setClear] = useState([]);
  const [result, setResult] = useState({});
  async function save(e) {
    e.preventDefault();
    const values = {};
    for (const s of q.data) { const v = draft[s.name]; if (v === undefined) continue; if (s.kind === "bool") values[s.name] = v; else if (s.secret) { if (v.trim()) values[s.name] = v.trim(); } else if (String(v) !== String(s.value ?? "")) values[s.name] = String(v); }
    if (await act(() => api("/admin/settings", { method: "PUT", body: JSON.stringify({ values, clear }) }), { ok: "Settings saved. They apply immediately.", invalidate: ["admin"] })) { setDraft({}); setClear([]); }
  }
  async function test(what) { setResult({ ...result, [what]: "Testing…" }); try { const r = await post(`/admin/settings/test/${what}`); setResult((x) => ({ ...x, [what]: r.message })); } catch (e) { setResult((x) => ({ ...x, [what]: e.message })); } }
  if (q.isLoading) return <Skeleton rows={4} />;
  if (q.error) return <ErrorBox error={q.error} />;
  return (
    <form onSubmit={save} className="max-w-3xl space-y-6">
      <p className="rounded-xl bg-bg px-4 py-3 text-sm text-mute">Keys and passwords are encrypted before they are stored and are never shown again. Every change is written to the audit log (names only, never values). Saved values override the server's environment variables.</p>
      {Object.entries(GROUPS).map(([g, title]) => (
        <section key={g} className="card space-y-3 p-6"><h2 className="font-display text-lg font-bold">{title}</h2>
          {q.data.filter((s) => s.group === g).map((s) => <SettingField key={s.name} s={s} draft={draft} setDraft={setDraft} clear={clear} setClear={setClear} />)}
          {(g === "assistant" || g === "email") && <div className="flex flex-wrap items-center gap-3 pt-1"><button type="button" className="btn btn-outline btn-sm" onClick={() => test(g === "email" ? "email" : "assistant")}>{g === "email" ? "Send a test email to me" : "Test the Groq key"}</button><span className="text-sm text-mute" role="status">{result[g === "email" ? "email" : "assistant"]}</span></div>}
        </section>))}
      <button className="btn btn-primary">Save settings</button>
    </form>
  );
}

function Inner() {
  const [tab, setTab] = useUrlState("tab", "overview");
  const seen = useSeen();
  const { dots } = useDots();
  const map = { clinics: "admin_clinics", support: "admin_support" };
  useEffect(() => { const c = map[tab]; if (c && dots[c]) seen(c); }, [tab, dots]); // eslint-disable-line react-hooks/exhaustive-deps
  const tabDots = { clinics: dots.admin_clinics, support: dots.admin_support };
  return (
    <>
      <PageHeader title="Platform admin" sub="Every clinic, user and change on the platform, plus the settings that run it." />
      {tab === "overview" && <Overview />}{tab === "clinics" && <Clinics />}{tab === "users" && <Users />}{tab === "audit" && <Audit />}{tab === "support" && <Support />}{tab === "messaging" && <Messaging />}{tab === "health" && <Health />}{tab === "settings" && <Settings />}
    </>
  );
}
export default function Admin() { return <Suspense fallback={<Skeleton rows={4} />}><Inner /></Suspense>; }
