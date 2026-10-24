"use client";
import { MapPin, Search } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import AuthLayout from "@/components/AuthLayout";
import { DateField } from "@/components/DateTime";
import { Field } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function PatientSignup() {
  const { registerPatient } = useAuth();
  const router = useRouter();
  const [q, setQ] = useState("");
  const [found, setFound] = useState(null);
  const [clinic, setClinic] = useState(null);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    if (q.trim().length < 2) { setFound(null); return; }
    const t = setTimeout(() => api(`/public/clinics?q=${encodeURIComponent(q.trim())}`).then(setFound).catch(() => setFound([])), 250);
    return () => clearTimeout(t);
  }, [q]);
  async function submit(e) {
    e.preventDefault();
    if (!clinic) return setErr("Choose your clinic first.");
    const f = new FormData(e.currentTarget);
    if (f.get("password") !== f.get("confirm")) return setErr("The passwords don't match.");
    setBusy(true); setErr("");
    try {
      await registerPatient({ clinic_id: clinic.id, full_name: f.get("full_name").trim(), email: f.get("email").trim(), phone: f.get("phone") || undefined, date_of_birth: f.get("date_of_birth") || undefined, password: f.get("password"), accept_terms: !!f.get("terms") });
      router.replace("/portal");
    } catch (x) { setErr(x.message); setBusy(false); }
  }
  return (
    <AuthLayout patient>
      <h1 className="font-display text-3xl font-extrabold tracking-tight">Create a patient account</h1>
      <p className="mt-2 text-mute">Free. You will be registered with the clinic you choose.</p>
      <form onSubmit={submit} className="mt-8 space-y-4">
        <div><p className="mb-1.5 text-sm font-medium">Your clinic</p>
          {clinic ? <div className="flex items-center justify-between rounded-btn border border-brand bg-accent-soft px-4 py-3 text-brand"><span className="font-semibold">{clinic.name}<span className="ml-2 text-sm font-normal">{clinic.city}</span></span><button type="button" className="text-sm underline" onClick={() => setClinic(null)}>Change</button></div> : (<>
            <div className="relative"><Search className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-mute" aria-hidden="true" /><input aria-label="Search for your clinic" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search by clinic name or city" className="field pl-10" /></div>
            {found && <ul className="mt-2 max-h-48 divide-y divide-line overflow-y-auto rounded-btn border border-line bg-surface" role="listbox">{found.length === 0 ? <li className="px-4 py-3 text-sm text-mute">No clinic found. Ask your clinic for its sign-up link.</li> : found.map((c) => (
              <li key={c.id}><button type="button" role="option" aria-selected="false" onClick={() => setClinic(c)} className="flex w-full items-center justify-between px-4 py-3 text-left hover:bg-bg"><span className="font-medium">{c.name}</span><span className="flex items-center gap-1 text-xs text-mute"><MapPin className="h-3 w-3" aria-hidden="true" />{c.city}</span></button></li>))}</ul>}</>)}</div>
        <Field label="Full name"><input name="full_name" required minLength={2} autoComplete="name" className="field" /></Field>
        <div className="grid gap-4 sm:grid-cols-2"><Field label="Email"><input name="email" type="email" required autoComplete="email" className="field" /></Field><Field label="Phone (optional)"><input name="phone" type="tel" autoComplete="tel" className="field" /></Field></div>
        <Field label="Date of birth (optional)"><DateField name="date_of_birth" label="Date of birth" max={new Date().toISOString().slice(0, 10)} /></Field>
        <div className="grid gap-4 sm:grid-cols-2"><Field label="Password" hint="At least 8 characters."><input name="password" type="password" required minLength={8} autoComplete="new-password" className="field" /></Field><Field label="Confirm password"><input name="confirm" type="password" required minLength={8} autoComplete="new-password" className="field" /></Field></div>
        <label className="flex items-start gap-2 text-sm text-mute"><input name="terms" type="checkbox" required className="mt-1" />I agree to the clinic holding my health information to provide my care, and to the terms and privacy policy.</label>
        {err && <p role="alert" className="rounded-btn bg-danger/10 px-4 py-3 text-sm text-danger-ink">{err}</p>}
        <button className="btn btn-primary w-full" disabled={busy}>{busy ? "Creating…" : "Create account"}</button>
      </form>
      <p className="mt-6 text-sm text-mute">Already registered? <Link href="/patient/login" className="font-semibold text-brand">Patient login</Link></p>
    </AuthLayout>
  );
}
