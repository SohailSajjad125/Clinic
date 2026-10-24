"use client";
import Link from "next/link";
import { useState } from "react";
import AuthLayout from "@/components/AuthLayout";
import { Field } from "@/components/ui";
import { post } from "@/lib/api";

export default function Forgot() {
  const [done, setDone] = useState(false);
  const [err, setErr] = useState("");
  async function submit(e) {
    e.preventDefault(); setErr("");
    try { await post("/auth/forgot-password", { email: e.currentTarget.email.value.trim() }); setDone(true); } catch (x) { setErr(x.message); }
  }
  return (
    <AuthLayout>
      <h1 className="font-display text-3xl font-extrabold tracking-tight">Reset your password</h1>
      {done ? <p role="status" className="mt-4 leading-7 text-mute">If an account exists for that email, we've sent a link to choose a new password. It expires in one hour.</p> : (
        <form onSubmit={submit} className="mt-8 space-y-5"><Field label="Email"><input name="email" type="email" required className="field" /></Field>
          {err && <p role="alert" className="text-sm text-danger-ink">{err}</p>}<button className="btn btn-primary w-full">Send reset link</button></form>)}
      <p className="mt-6 text-sm"><Link href="/login" className="font-semibold text-brand">Back to log in</Link></p>
    </AuthLayout>
  );
}
