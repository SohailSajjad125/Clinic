"use client";
import { zodResolver } from "@hookform/resolvers/zod";
import { CheckCircle2 } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { postJSON } from "@/lib/api";

const schema = z.object({
  name: z.string().trim().min(2, "Enter your name"),
  email: z.string().trim().email("Enter a valid email address"),
  clinic_name: z.string().max(160).optional(),
  phone: z.string().max(30).optional(),
  topic: z.enum(["demo", "sales", "support", "partnership", "other"]),
  message: z.string().trim().min(10, "Tell us a little more (at least 10 characters)").max(2000, "Please keep it under 2000 characters"),
  website: z.string().max(0).optional(),
});

function Field({ label, error, children, id }) {
  return (
    <div>
      <label htmlFor={id} className="mb-1.5 block text-sm font-medium">{label}</label>
      {children}
      {error && <p role="alert" className="mt-1.5 text-sm text-danger-ink">{error}</p>}
    </div>
  );
}

export default function ContactForm() {
  const [done, setDone] = useState(false);
  const [serverError, setServerError] = useState("");
  const { register, handleSubmit, reset, formState: { errors, isSubmitting } } = useForm({ resolver: zodResolver(schema), defaultValues: { topic: "demo" } });

  async function onSubmit(values) {
    setServerError("");
    try { await postJSON("/public/contact", values); reset(); setDone(true); }
    catch (e) { setServerError(e.message); }
  }

  if (done) {
    return (
      <div role="status" className="rounded-card border border-line bg-surface p-10 text-center">
        <CheckCircle2 className="mx-auto h-10 w-10 text-brand" aria-hidden="true" />
        <h3 className="mt-4 font-display text-2xl font-bold">Message received</h3>
        <p className="mx-auto mt-2 max-w-sm text-mute">Thank you. We'll reply to the email you provided.</p>
        <button className="btn btn-outline mt-6" onClick={() => setDone(false)}>Send another message</button>
      </div>
    );
  }
  return (
    <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-5 rounded-card border border-line bg-surface p-6 sm:p-8">
      <div className="grid gap-5 sm:grid-cols-2">
        <Field label="Your name" id="c-name" error={errors.name?.message}><input id="c-name" autoComplete="name" className="field" {...register("name")} /></Field>
        <Field label="Email" id="c-email" error={errors.email?.message}><input id="c-email" type="email" autoComplete="email" className="field" {...register("email")} /></Field>
        <Field label="Clinic name (optional)" id="c-clinic" error={errors.clinic_name?.message}><input id="c-clinic" autoComplete="organization" className="field" {...register("clinic_name")} /></Field>
        <Field label="Phone (optional)" id="c-phone" error={errors.phone?.message}><input id="c-phone" type="tel" autoComplete="tel" className="field" {...register("phone")} /></Field>
      </div>
      <Field label="What can we help with?" id="c-topic" error={errors.topic?.message}>
        <select id="c-topic" className="field" {...register("topic")}>
          <option value="demo">Book a demo</option><option value="sales">Pricing and plans</option><option value="support">Support</option>
          <option value="partnership">Partnership</option><option value="other">Something else</option>
        </select>
      </Field>
      <Field label="Message" id="c-message" error={errors.message?.message}><textarea id="c-message" rows={5} className="field" {...register("message")} /></Field>
      <input tabIndex={-1} autoComplete="off" aria-hidden="true" className="hidden" {...register("website")} />
      {serverError && <p role="alert" className="rounded-btn bg-danger/10 px-4 py-3 text-sm text-danger-ink">{serverError}</p>}
      <button className="btn btn-primary w-full sm:w-auto" disabled={isSubmitting}>{isSubmitting ? "Sending…" : "Send message"}</button>
    </form>
  );
}
