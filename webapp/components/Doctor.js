"use client";
import { Award, Clock, Phone, Stethoscope } from "lucide-react";
import { Field } from "./ui";
import { money } from "@/lib/hooks";

const DAYS = [["mon", "Mon"], ["tue", "Tue"], ["wed", "Wed"], ["thu", "Thu"], ["fri", "Fri"], ["sat", "Sat"], ["sun", "Sun"]];
const DEFAULT_DAYS = ["mon", "tue", "wed", "thu", "fri", "sat"];

/** The fields that describe a doctor. Uncontrolled: read the values with DoctorForm.read(formElement). */
export function DoctorForm({ initial }) {
  const p = initial || {};
  const days = p.available_days || DEFAULT_DAYS;
  return (
    <fieldset className="space-y-4 rounded-xl border border-line p-4"><legend className="px-2 text-sm font-semibold">Doctor details</legend>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Specialization"><input name="specialization" defaultValue={p.specialization || ""} placeholder="e.g. Cardiology" maxLength={80} className="field" /></Field>
        <Field label="Qualifications"><input name="qualifications" defaultValue={p.qualifications || ""} placeholder="e.g. MBBS, FCPS" maxLength={200} className="field" /></Field>
        <Field label="Medical licence number"><input name="license_no" defaultValue={p.license_no || ""} maxLength={40} className="field" /></Field>
        <Field label="Phone"><input name="phone" type="tel" defaultValue={p.phone || ""} maxLength={30} className="field" /></Field>
        <Field label="Years of experience"><input name="experience_years" type="number" min={0} max={70} defaultValue={p.experience_years ?? 0} className="field" /></Field>
        <Field label="Consultation fee (PKR)"><input name="consultation_fee" type="number" min={0} defaultValue={p.consultation_fee ?? 0} className="field" /></Field>
      </div>
      <Field label="About"><textarea name="bio" rows={2} maxLength={1000} defaultValue={p.bio || ""} className="field" /></Field>
      <div><p className="mb-2 text-sm font-medium">Working days</p><div className="flex flex-wrap gap-2">{DAYS.map(([k, l]) => <label key={k} className="chip cursor-pointer has-[:checked]:border-brand has-[:checked]:bg-accent-soft has-[:checked]:text-brand"><input type="checkbox" name={`day_${k}`} defaultChecked={days.includes(k)} className="sr-only" />{l}</label>)}</div></div>
      <div className="grid gap-4 sm:grid-cols-3">
        <Field label="Starts"><input name="start_time" type="time" step={300} defaultValue={p.start_time || "09:00"} required className="field" /></Field>
        <Field label="Ends"><input name="end_time" type="time" step={300} defaultValue={p.end_time || "17:00"} required className="field" /></Field>
        <Field label="Minutes per visit"><select name="slot_minutes" defaultValue={p.slot_minutes || 20} className="field">{[10, 15, 20, 30, 45, 60].map((m) => <option key={m} value={m}>{m} min</option>)}</select></Field>
      </div>
    </fieldset>
  );
}
DoctorForm.read = (form) => {
  const f = new FormData(form);
  return { specialization: f.get("specialization") || "", qualifications: f.get("qualifications") || "", license_no: f.get("license_no") || "", phone: f.get("phone") || "", bio: f.get("bio") || "",
    experience_years: Number(f.get("experience_years")) || 0, consultation_fee: Number(f.get("consultation_fee")) || 0, slot_minutes: Number(f.get("slot_minutes")) || 20,
    start_time: f.get("start_time"), end_time: f.get("end_time"), available_days: DAYS.map(([k]) => k).filter((k) => f.get(`day_${k}`)) };
};

export function DoctorCard({ d, onEdit, onPick, picked }) {
  const p = d.profile || {};
  return (
    <div className={`card flex flex-col gap-3 p-5 ${picked ? "border-brand ring-1 ring-[var(--primary)]" : ""}`}>
      <div className="flex items-start gap-3"><span className="grid h-11 w-11 shrink-0 place-items-center rounded-full bg-accent-soft text-brand"><Stethoscope className="h-5 w-5" aria-hidden="true" /></span>
        <div className="min-w-0"><p className="font-display text-lg font-bold">{d.full_name}</p><p className="text-sm text-mute">{[p.specialization, p.qualifications].filter(Boolean).join(" · ") || "General practice"}</p></div></div>
      <ul className="space-y-1 text-sm text-mute">
        {p.experience_years > 0 && <li className="flex items-center gap-2"><Award className="h-4 w-4" aria-hidden="true" />{p.experience_years} years of experience</li>}
        <li className="flex items-center gap-2"><Clock className="h-4 w-4" aria-hidden="true" />{(p.available_days || []).map((x) => x[0].toUpperCase() + x.slice(1)).join(", ") || "No working days set"} · {p.start_time}–{p.end_time}</li>
        {p.phone && <li className="flex items-center gap-2"><Phone className="h-4 w-4" aria-hidden="true" />{p.phone}</li>}
      </ul>
      {p.bio && <p className="text-sm leading-6">{p.bio}</p>}
      <div className="mt-auto flex items-center justify-between gap-2"><p className="font-semibold">{p.consultation_fee ? money(p.consultation_fee) : "Fee on request"}</p>
        <div className="flex gap-2">{onEdit && <button className="btn btn-outline btn-sm" onClick={onEdit}>Edit</button>}{onPick && <button className="btn btn-primary btn-sm" onClick={onPick} aria-pressed={picked}>{picked ? "Selected" : "Choose"}</button>}</div></div>
    </div>
  );
}
