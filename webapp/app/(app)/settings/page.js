"use client";
import { Trash2 } from "lucide-react";
import { Suspense } from "react";
import { DoctorForm } from "@/components/Doctor";
import { useConfirm } from "@/components/Modal";
import { ErrorBox, Field, PageHeader, Skeleton, Tabs } from "@/components/ui";
import { del, patch, post } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { fmtDateTime, money, useAct, useApi, useUrlState } from "@/lib/hooks";

const DAYS = [["mon", "Monday"], ["tue", "Tuesday"], ["wed", "Wednesday"], ["thu", "Thursday"], ["fri", "Friday"], ["sat", "Saturday"], ["sun", "Sunday"]];

function ClinicTab({ owner }) {
  const act = useAct();
  const c = useApi("clinic", "/clinic");
  if (c.isLoading) return <Skeleton rows={4} />;
  const wh = c.data.working_hours || {};
  async function save(e) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const working_hours = Object.fromEntries(DAYS.map(([k]) => [k, f.get(`${k}_closed`) ? null : { open: f.get(`${k}_open`), close: f.get(`${k}_close`) }]));
    act(() => patch("/clinic", { name: f.get("name"), clinic_type: f.get("clinic_type"), city: f.get("city"), country: f.get("country"), working_hours, public_listing: !!f.get("public_listing") }), { ok: "Clinic updated", invalidate: ["clinic"] });
  }
  return (
    <form key={JSON.stringify(c.data)} onSubmit={save} className="card grid gap-4 p-6 sm:grid-cols-2">
      <Field label="Clinic name"><input name="name" defaultValue={c.data.name} disabled={!owner} required className="field" /></Field>
      <Field label="Type"><input name="clinic_type" defaultValue={c.data.clinic_type} disabled={!owner} required className="field" /></Field>
      <Field label="City"><input name="city" defaultValue={c.data.city} disabled={!owner} className="field" /></Field>
      <Field label="Country"><input name="country" defaultValue={c.data.country} disabled={!owner} className="field" /></Field>
      <fieldset className="sm:col-span-2"><legend className="mb-2 text-sm font-medium">Working hours</legend>
        <div className="space-y-2">{DAYS.map(([k, l]) => {
          const d = wh[k]; const closed = k in wh && d === null;
          return <div key={k} className="grid grid-cols-[110px_1fr_1fr_auto] items-center gap-2 text-sm"><span>{l}</span>
            <input name={`${k}_open`} type="time" defaultValue={d?.open || "09:00"} disabled={!owner} aria-label={`${l} opens`} className="field" /><input name={`${k}_close`} type="time" defaultValue={d?.close || "17:00"} disabled={!owner} aria-label={`${l} closes`} className="field" />
            <label className="flex items-center gap-1.5 text-mute"><input name={`${k}_closed`} type="checkbox" defaultChecked={closed} disabled={!owner} />Closed</label></div>;
        })}</div></fieldset>
      <label className="flex items-start gap-2 text-sm sm:col-span-2"><input name="public_listing" type="checkbox" defaultChecked={c.data.public_listing !== false} disabled={!owner} className="mt-1" /><span><b>Let patients find this clinic</b> when they sign up online. Turn off to accept only patients you invite.</span></label>
      {owner && <div className="sm:col-span-2"><button className="btn btn-primary">Save changes</button></div>}
    </form>
  );
}

function ListTab({ title, path, fields, canWrite, keyName, render }) {
  const act = useAct();
  const confirm = useConfirm();
  const list = useApi(keyName, path);
  async function add(e) {
    e.preventDefault();
    const f = e.currentTarget; const fd = Object.fromEntries(new FormData(f));
    for (const k of Object.keys(fd)) if (fields.find((x) => x.name === k)?.type === "number") fd[k] = Number(fd[k]) || 0;
    if (await act(() => post(path, fd), { ok: "Added", invalidate: [keyName] })) f.reset();
  }
  async function remove(o, label) {
    if (await confirm({ title: `Delete ${label}?`, body: "This is a setting, so it is removed immediately.", action: "Delete", danger: true })) act(() => del(`${path}/${o.id}`), { ok: "Deleted", invalidate: [keyName] });
  }
  return (
    <div className="space-y-4">
      {canWrite && <form onSubmit={add} className="card flex flex-wrap items-end gap-3 p-5">{fields.map((f) => <div key={f.name} className="min-w-[140px] flex-1"><Field label={f.label}><input name={f.name} type={f.type || "text"} required={f.required} min={f.type === "number" ? 0 : undefined} className="field" /></Field></div>)}<button className="btn btn-primary">Add</button></form>}
      <ErrorBox error={list.error} />
      {list.isLoading ? <Skeleton rows={2} /> : list.data.length === 0 ? <p className="text-mute">No {title.toLowerCase()} yet.</p> : (
        <div className="card divide-y divide-line">{list.data.map((o) => <div key={o.id} className="flex items-center justify-between gap-3 px-5 py-3 text-sm"><span>{render(o)}</span>
          {canWrite && <button onClick={() => remove(o, render(o).toString().slice(0, 40))} aria-label="Delete" className="rounded-lg p-2 text-mute hover:bg-danger/10 hover:text-danger-ink"><Trash2 className="h-4 w-4" /></button>}</div>)}</div>)}
    </div>
  );
}

function ProfileTab() {
  const act = useAct();
  const q = useApi("my-profile", "/me/profile");
  if (q.isLoading) return <Skeleton rows={3} />;
  if (q.error) return <ErrorBox error={q.error} />;
  return (
    <form key={JSON.stringify(q.data)} onSubmit={(e) => { e.preventDefault(); act(() => patch("/me/profile", DoctorForm.read(e.currentTarget)), { ok: "Profile saved. Patients see this when booking.", invalidate: ["my-profile", "doctors"] }); }} className="card max-w-3xl space-y-4 p-6">
      <p className="text-sm text-mute">This is what patients and colleagues see, and it decides which times patients can book with you.</p>
      <DoctorForm initial={q.data.profile} /><button className="btn btn-primary">Save profile</button></form>
  );
}

function PlanTab() {
  const c = useApi("clinic", "/clinic");
  if (c.isLoading) return <Skeleton rows={3} />;
  const { plan, limits, usage } = c.data;
  const row = (k, label) => <div className="flex justify-between py-2"><span className="text-mute">{label}</span><span className="font-semibold">{usage[k]}{limits[k] ? ` / ${limits[k]}` : ""}</span></div>;
  return (
    <div className="card max-w-lg p-6"><p className="text-sm text-mute">Current plan</p><p className="font-display text-3xl font-extrabold capitalize">{plan}</p>
      <div className="mt-4 divide-y divide-line">{row("patients", "Patients")}{row("staff", "Team members")}{row("doctors", "Doctors")}</div>
      <p className="mt-4 text-sm text-mute">Plans are managed by our team. To upgrade, use the Contact page on our website and mention your clinic name.</p></div>
  );
}

function SecurityTab() {
  const act = useAct();
  const confirm = useConfirm();
  const sessions = useApi("sessions", "/auth/sessions");
  async function change(e) {
    e.preventDefault();
    const f = e.currentTarget; const fd = new FormData(f);
    if (fd.get("new_password") !== fd.get("confirm")) return act(async () => { throw new Error("The new passwords don't match."); });
    if (await act(() => post("/auth/change-password", { current_password: fd.get("current_password"), new_password: fd.get("new_password") }), { ok: "Password changed. Other devices were signed out.", invalidate: ["sessions"] })) f.reset();
  }
  async function revoke(s) {
    if (await confirm({ title: "Sign out this device?", body: s.device, action: "Sign out", danger: true })) act(() => del(`/auth/sessions/${s.id}`), { ok: "Device signed out", invalidate: ["sessions"] });
  }
  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <form onSubmit={change} className="card space-y-4 p-6"><h2 className="font-display text-lg font-bold">Change password</h2>
        <Field label="Current password"><input name="current_password" type="password" required autoComplete="current-password" className="field" /></Field>
        <Field label="New password" hint="At least 8 characters."><input name="new_password" type="password" minLength={8} required autoComplete="new-password" className="field" /></Field>
        <Field label="Confirm new password"><input name="confirm" type="password" minLength={8} required autoComplete="new-password" className="field" /></Field><button className="btn btn-primary">Change password</button></form>
      <section className="card p-6"><h2 className="font-display text-lg font-bold">Signed-in devices</h2>
        <ul className="mt-3 divide-y divide-line">{(sessions.data || []).map((s) => <li key={s.id} className="flex items-center justify-between gap-3 py-3 text-sm"><div><p className="max-w-[260px] truncate font-medium">{s.device}{s.current && <span className="ml-2 text-xs text-brand">This device</span>}</p><p className="text-xs text-mute">Last used {fmtDateTime(s.last_used)}</p></div>
          {!s.current && <button className="btn btn-outline btn-sm" onClick={() => revoke(s)}>Sign out</button>}</li>)}</ul></section>
    </div>
  );
}

function Inner() {
  const { me } = useAuth();
  const [wanted, setTab] = useUrlState("tab", me.role === "doctor" ? "profile" : "clinic");
  const owner = me.role === "owner";
  if (me.role === "nurse") return <ErrorBox error={new Error("Settings are not available for your role.")} />;
  const tabs = me.role === "doctor" ? [["profile", "My doctor profile"]]
    : [...(me.role === "owner" ? [["profile", "My doctor profile"]] : []), ["clinic", "Clinic & hours"], ["services", "Services"], ...(owner ? [["templates", "Medicine templates"]] : []), ["locations", "Locations"], ["plan", "Plan & usage"], ["security", "Security"]];
  const tab = tabs.some(([k]) => k === wanted) ? wanted : tabs[0][0];                // a typed-in address can't reveal a tab this role doesn't have
  return (
    <>
      <PageHeader title="Settings" sub={me.clinic?.name} />
      {tabs.length > 1 && <Tabs tabs={tabs} value={tab} onChange={setTab} />}
      {tab === "profile" && <ProfileTab />}
      {tab === "clinic" && <ClinicTab owner={owner} />}
      {tab === "services" && <ListTab title="Services" path="/services" keyName="services" canWrite={owner} fields={[{ name: "name", label: "Service", required: true }, { name: "price", label: "Price (PKR)", type: "number", required: true }]} render={(o) => `${o.name} · ${money(o.price)}`} />}
      {tab === "templates" && <ListTab title="Templates" path="/medicine-templates" keyName="templates" canWrite fields={[{ name: "medicine", label: "Medicine", required: true }, { name: "dose", label: "Dose" }, { name: "frequency", label: "Frequency" }, { name: "duration", label: "Duration" }]} render={(o) => [o.medicine, o.dose, o.frequency, o.duration].filter(Boolean).join(" · ")} />}
      {tab === "locations" && <ListTab title="Locations" path="/locations" keyName="locations" canWrite={owner} fields={[{ name: "name", label: "Branch name", required: true }, { name: "address", label: "Address" }]} render={(o) => `${o.name}${o.address ? ` · ${o.address}` : ""}`} />}
      {tab === "plan" && <PlanTab />}
      {tab === "security" && <SecurityTab />}
    </>
  );
}
export default function Settings() { return <Suspense fallback={<Skeleton />}><Inner /></Suspense>; }
