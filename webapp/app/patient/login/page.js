"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import AuthLayout from "@/components/AuthLayout";
import { Field } from "@/components/ui";
import { useAuth } from "@/lib/auth";

export default function PatientLogin() {
  const { login } = useAuth();
  const router = useRouter();
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit(e) {
    e.preventDefault();
    const f = e.currentTarget;
    setBusy(true); setErr("");
    try { await login(f.email.value.trim(), f.password.value, "patient"); router.replace("/portal"); }
    catch (x) { setErr(x.message); setBusy(false); }
  }
  return (
    <AuthLayout patient>
      <h1 className="font-display text-3xl font-extrabold tracking-tight">Patient login</h1>
      <p className="mt-2 text-mute">See your appointments, prescriptions and reports.</p>
      <form onSubmit={submit} className="mt-8 space-y-5">
        <Field label="Email"><input name="email" type="email" required autoComplete="email" className="field" /></Field>
        <Field label="Password"><input name="password" type="password" required autoComplete="current-password" className="field" /></Field>
        {err && <p role="alert" className="rounded-btn bg-danger/10 px-4 py-3 text-sm text-danger-ink">{err}</p>}
        <button className="btn btn-primary w-full" disabled={busy}>{busy ? "Signing in…" : "Log in"}</button>
      </form>
      <p className="mt-4 text-sm"><Link href="/forgot-password" className="font-semibold text-brand">Forgot your password?</Link></p>
      <p className="mt-4 text-sm text-mute">New here? <Link href="/patient/signup" className="font-semibold text-brand">Create a patient account</Link></p>
      <p className="mt-2 text-sm text-mute">Clinic staff? <Link href="/login" className="font-semibold text-brand">Staff login</Link></p>
    </AuthLayout>
  );
}
