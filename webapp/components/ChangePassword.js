"use client";
import { useState } from "react";
import Logo from "./Logo";
import { Field } from "./ui";
import { post } from "@/lib/api";

/** Shown instead of the app when an administrator set this account's password. Nothing else works until it is changed. */
export default function ChangePassword({ onDone, onLogout }) {
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit(e) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    if (f.get("new_password") !== f.get("confirm")) return setErr("The new passwords don't match.");
    setBusy(true); setErr("");
    try { await post("/auth/change-password", { current_password: f.get("current_password"), new_password: f.get("new_password") }); await onDone(); }
    catch (x) { setErr(x.message); setBusy(false); }
  }
  return (
    <main className="grid min-h-screen place-items-center p-6">
      <form onSubmit={submit} className="card w-full max-w-md space-y-5 p-8">
        <Logo />
        <div><h1 className="font-display text-2xl font-extrabold">Choose your own password</h1>
          <p className="mt-2 text-sm leading-6 text-mute">Your account was set up with a temporary password that someone else knows. Replace it to continue.</p></div>
        <Field label="Temporary password"><input name="current_password" type="password" required autoComplete="current-password" className="field" /></Field>
        <Field label="New password" hint="At least 8 characters, and not a common password."><input name="new_password" type="password" required minLength={8} autoComplete="new-password" className="field" /></Field>
        <Field label="Confirm new password"><input name="confirm" type="password" required minLength={8} autoComplete="new-password" className="field" /></Field>
        {err && <p role="alert" className="rounded-btn bg-danger/10 px-4 py-3 text-sm text-danger-ink">{err}</p>}
        <button className="btn btn-primary w-full" disabled={busy}>{busy ? "Saving…" : "Save and continue"}</button>
        <button type="button" onClick={onLogout} className="w-full text-center text-sm text-mute hover:text-ink">Log out</button>
      </form>
    </main>
  );
}
