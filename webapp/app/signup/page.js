"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import AuthLayout from "@/components/AuthLayout";
import { Field } from "@/components/ui";
import { useAuth } from "@/lib/auth";

const TYPES = ["General practice", "Dental", "Physiotherapy", "Dermatology", "Multi-specialty", "Diagnostic centre", "Other"];

export default function Signup() {
  const { register } = useAuth();
  const router = useRouter();
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit(e) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    if (f.get("password").length < 8) return setErr("Use a password of at least 8 characters.");
    setBusy(true); setErr("");
    try {
      const r = await register({ clinic_name: f.get("clinic_name").trim(), clinic_type: f.get("clinic_type"), city: f.get("city").trim(), country: f.get("country").trim(),
        full_name: f.get("full_name").trim(), email: f.get("email").trim(), password: f.get("password") });
      router.replace(r?.me?.role === "patient" ? "/portal" : r?.me?.role === "superadmin" ? "/admin" : "/onboarding");
    } catch (x) { setErr(x.message); setBusy(false); }
  }
  return (
    <AuthLayout>
      <h1 className="font-display text-3xl font-extrabold tracking-tight">Create your clinic</h1>
      <p className="mt-2 text-mute">Free to start. You'll be the clinic owner.</p>
      <form onSubmit={submit} className="mt-8 space-y-4">
        <Field label="Clinic name"><input name="clinic_name" required minLength={2} className="field" /></Field>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Clinic type"><select name="clinic_type" className="field">{TYPES.map((t) => <option key={t}>{t}</option>)}</select></Field>
          <Field label="City"><input name="city" required className="field" /></Field>
        </div>
        <Field label="Country"><input name="country" required defaultValue="Pakistan" className="field" /></Field>
        <Field label="Your name"><input name="full_name" required minLength={2} autoComplete="name" className="field" /></Field>
        <Field label="Email"><input name="email" type="email" required autoComplete="email" className="field" /></Field>
        <Field label="Password" hint="At least 8 characters."><input name="password" type="password" required minLength={8} autoComplete="new-password" className="field" /></Field>
        {err && <p role="alert" className="rounded-btn bg-danger/10 px-4 py-3 text-sm text-danger-ink">{err}</p>}
        <button className="btn btn-primary w-full" disabled={busy}>{busy ? "Creating…" : "Create clinic"}</button>
      </form>
      <p className="mt-6 text-sm text-mute">Already have an account? <Link href="/login" className="font-semibold text-brand">Log in</Link></p>
    </AuthLayout>
  );
}
