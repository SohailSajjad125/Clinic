"use client";
import { Calendar, CreditCard, Search, Settings, User, UserPlus, Users } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { Modal } from "./Modal";
import { api } from "@/lib/api";

const CMDS = [
  ["New patient", "/patients?new=1", UserPlus, ["owner", "receptionist", "nurse"]], ["New appointment", "/appointments?new=1", Calendar, ["owner", "doctor", "receptionist", "nurse"]],
  ["New invoice", "/billing?new=1", CreditCard, ["owner", "receptionist"]], ["Open queue", "/queue", Users, ["owner", "doctor", "receptionist", "nurse"]], ["Open settings", "/settings", Settings, ["owner", "doctor", "receptionist"]],
];

export default function Palette({ open, onClose, role }) {
  const router = useRouter();
  const [q, setQ] = useState("");
  const [hits, setHits] = useState([]);
  const [i, setI] = useState(0);
  useEffect(() => { if (open) { setQ(""); setHits([]); setI(0); } }, [open]);
  useEffect(() => {
    if (!open || q.trim().length < 2 || role === "patient") { setHits([]); return; }
    const t = setTimeout(() => api(`/patients?q=${encodeURIComponent(q.trim())}&limit=6`).then(setHits).catch(() => setHits([])), 200);
    return () => clearTimeout(t);
  }, [q, open, role]);
  const rows = useMemo(() => [
    ...hits.map((p) => ({ label: p.full_name, hint: p.phone || "Patient", href: `/patients/${p.id}`, Icon: User })),
    ...CMDS.filter(([l, , , r]) => r.includes(role) && l.toLowerCase().includes(q.trim().toLowerCase())).map(([label, href, Icon]) => ({ label, href, Icon, hint: "Action" })),
  ], [hits, q, role]);
  const go = (r) => { onClose(); router.push(r.href); };
  const onKey = (e) => {
    if (e.key === "ArrowDown") { e.preventDefault(); setI((x) => Math.min(x + 1, rows.length - 1)); }
    if (e.key === "ArrowUp") { e.preventDefault(); setI((x) => Math.max(x - 1, 0)); }
    if (e.key === "Enter" && rows[i]) go(rows[i]);
  };
  return (
    <Modal open={open} onClose={onClose} title="Search or jump to…">
      <div className="relative"><Search className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-mute" aria-hidden="true" />
        <input value={q} onChange={(e) => { setQ(e.target.value); setI(0); }} onKeyDown={onKey} placeholder="Search a patient or type a command" className="field pl-10" aria-label="Command" /></div>
      <ul className="mt-3 max-h-72 space-y-1 overflow-y-auto" role="listbox">
        {rows.length === 0 && <li className="px-3 py-6 text-center text-sm text-mute">Nothing found.</li>}
        {rows.map((r, n) => (
          <li key={r.href + r.label} role="option" aria-selected={n === i}>
            <button onClick={() => go(r)} onMouseEnter={() => setI(n)} className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm ${n === i ? "bg-accent-soft text-brand" : ""}`}>
              <r.Icon className="h-4 w-4 shrink-0" aria-hidden="true" /><span className="flex-1 font-medium">{r.label}</span><span className="text-xs text-mute">{r.hint}</span></button></li>))}
      </ul>
    </Modal>
  );
}
