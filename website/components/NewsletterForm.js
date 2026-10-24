"use client";
import { useState } from "react";
import { postJSON } from "@/lib/api";

export default function NewsletterForm() {
  const [state, setState] = useState({ status: "idle", msg: "" });
  async function onSubmit(e) {
    e.preventDefault();
    const f = e.currentTarget;
    const email = f.email.value.trim();
    if (!/^\S+@\S+\.\S+$/.test(email)) return setState({ status: "error", msg: "Enter a valid email address." });
    setState({ status: "loading", msg: "" });
    try {
      await postJSON("/public/newsletter", { email, website: f.website.value });
      f.reset();
      setState({ status: "done", msg: "You're subscribed. Thank you." });
    } catch (err) { setState({ status: "error", msg: err.message }); }
  }
  return (
    <form onSubmit={onSubmit} noValidate aria-label="Newsletter signup">
      <div className="flex gap-2">
        <label htmlFor="nl-email" className="sr-only">Email address</label>
        <input id="nl-email" name="email" type="email" autoComplete="email" placeholder="you@clinic.com" className="field" />
        <input name="website" tabIndex={-1} autoComplete="off" aria-hidden="true" className="hidden" />
        <button className="btn btn-primary" disabled={state.status === "loading"}>{state.status === "loading" ? "Joining…" : "Subscribe"}</button>
      </div>
      <p role="status" className={`mt-2 min-h-5 text-sm ${state.status === "error" ? "text-danger-ink" : "text-mute"}`}>{state.msg}</p>
    </form>
  );
}
