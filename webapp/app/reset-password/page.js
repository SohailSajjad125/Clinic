"use client";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import AuthLayout from "@/components/AuthLayout";
import { Field } from "@/components/ui";
import { post } from "@/lib/api";

function Inner() {
  const token = useSearchParams().get("token") || "";
  const [state, setState] = useState({ done: false, err: "" });
  async function submit(e) {
    e.preventDefault();
    const pw = e.currentTarget.password.value;
    if (pw !== e.currentTarget.confirm.value) return setState({ done: false, err: "The passwords don't match." });
    try { await post("/auth/reset-password", { token, password: pw }); setState({ done: true, err: "" }); } catch (x) { setState({ done: false, err: x.message }); }
  }
  return (
    <AuthLayout>
      <h1 className="font-display text-3xl font-extrabold tracking-tight">Choose a new password</h1>
      {state.done ? <p role="status" className="mt-4 text-mute">Your password was changed. <Link href="/login" className="font-semibold text-brand">Log in</Link></p> : (
        <form onSubmit={submit} className="mt-8 space-y-5">
          <Field label="New password" hint="At least 8 characters."><input name="password" type="password" minLength={8} required autoComplete="new-password" className="field" /></Field>
          <Field label="Confirm password"><input name="confirm" type="password" minLength={8} required autoComplete="new-password" className="field" /></Field>
          {state.err && <p role="alert" className="text-sm text-danger-ink">{state.err}</p>}<button className="btn btn-primary w-full" disabled={!token}>Change password</button></form>)}
    </AuthLayout>
  );
}
export default function Reset() { return <Suspense><Inner /></Suspense>; }
