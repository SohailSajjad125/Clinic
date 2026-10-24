"use client";
import { CalendarDays } from "lucide-react";
import { useEffect, useMemo } from "react";
import { addDays, dayKey, tzOffset, useApi } from "@/lib/hooks";

const wd = (k) => new Date(`${k}T12:00:00`).toLocaleDateString("en-GB", { weekday: "short" });
const dm = (k) => new Date(`${k}T12:00:00`).toLocaleDateString("en-GB", { day: "numeric", month: "short" });

/** A date with one-tap shortcuts. `quick` is a list of [label, days-from-today]. Works in light and dark themes. */
export function DateField({ name, value, defaultValue, onChange, min, max, quick = [], required, label = "Date", className = "" }) {
  const today = dayKey();
  return (
    <div className={className}>
      <div className="relative">
        <CalendarDays className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-mute" aria-hidden="true" />
        <input type="date" name={name} aria-label={label} required={required} min={min} max={max} {...(value !== undefined ? { value } : { defaultValue })}
          onChange={onChange ? (e) => onChange(e.target.value) : undefined} className="field pl-10" />
      </div>
      {quick.length > 0 && onChange && (
        <div className="mt-2 flex flex-wrap gap-2">{quick.map(([l, n]) => <button type="button" key={l} className="chip" aria-pressed={value === addDays(today, n)} onClick={() => onChange(addDays(today, n))}>{l}</button>)}</div>
      )}
    </div>
  );
}

/**
 * Pick a day, then pick a free time from the doctor's real schedule. Taken and past times are greyed out.
 * `endpoint` is "/slots" for staff or "/portal/slots" for patients. `value` / `onChange` use an ISO timestamp (UTC).
 */
export function SlotPicker({ endpoint = "/slots", doctorId, value, onChange, day, onDay }) {
  const today = dayKey();
  const days = useMemo(() => Array.from({ length: 7 }, (_, i) => addDays(today, i)), [today]);
  const q = useApi(["slots", endpoint, doctorId || "any", day], `${endpoint}?date=${day}&tz_offset_minutes=${tzOffset()}${doctorId ? `&doctor_id=${doctorId}` : ""}`, { staleTime: 0 });
  const slots = q.data || [];
  useEffect(() => { if (value && !slots.some((s) => s.start === value && !s.taken && !s.past)) { if (!q.isLoading) onChange(""); } }, [q.data]); // eslint-disable-line react-hooks/exhaustive-deps
  const part = (s) => { const h = Number(s.time.slice(0, 2)); return h < 12 ? "Morning" : h < 17 ? "Afternoon" : "Evening"; };
  const groups = ["Morning", "Afternoon", "Evening"].map((g) => [g, slots.filter((s) => part(s) === g)]).filter(([, l]) => l.length);
  return (
    <div className="space-y-3">
      <div className="flex gap-2 overflow-x-auto pb-1" role="group" aria-label="Choose a day">
        {days.map((d) => <button type="button" key={d} className="chip min-w-[64px] shrink-0 text-center leading-tight" aria-pressed={day === d} onClick={() => onDay(d)}><span className="block text-xs opacity-80">{d === today ? "Today" : wd(d)}</span><span className="block">{dm(d)}</span></button>)}
      </div>
      <label className="block text-xs text-mute">Another day<input type="date" min={today} value={day} onChange={(e) => e.target.value && onDay(e.target.value)} className="field mt-1" aria-label="Pick another day" /></label>
      {q.isLoading ? <p className="text-sm text-mute">Loading available times…</p> : groups.length === 0 ? (
        <p role="status" className="rounded-xl border border-dashed border-line px-4 py-5 text-sm text-mute">No times are available on this day. Try another day.</p>
      ) : groups.map(([g, list]) => (
        <div key={g}><p className="mb-1.5 text-xs font-semibold text-mute">{g}</p>
          <div className="flex flex-wrap gap-2">{list.map((s) => <button type="button" key={s.start} className="chip tabular-nums" disabled={s.taken || s.past} title={s.taken ? "Already booked" : s.past ? "Already passed" : ""} aria-pressed={value === s.start} onClick={() => onChange(s.start)}>{s.time}</button>)}</div></div>
      ))}
    </div>
  );
}
