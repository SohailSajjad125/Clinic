"use client";
import { ScrollText } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Empty, ErrorBox, PageHeader, Skeleton, Tabs } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { fmtDateTime, useApi } from "@/lib/hooks";

const ROLES = [["", "Everyone"], ["owner", "Owner"], ["doctor", "Doctors"], ["receptionist", "Reception"], ["nurse", "Nurses"], ["patient", "Patients"]];
const LABEL = {
  "clinic.created": "Created the clinic", "clinic.updated": "Changed clinic settings", "auth.login": "Logged in", "staff.added": "Added a team member", "staff.deleted": "Removed a team member", "staff.restored": "Restored a team member",
  "staff.purged": "Permanently deleted a team member", "staff.permissions": "Changed a permission", "staff.message_sent": "Replied to a patient message", "patient.created": "Added a patient", "patient.updated": "Edited a patient",
  "patient.deleted": "Deleted a patient", "patient.self_registered": "Signed up as a patient", "portal.invited": "Gave a patient portal access", "portal.revoked": "Removed portal access", "portal.appointment_requested": "Requested an appointment",
  "portal.appointment_cancelled": "Cancelled their appointment", "portal.message_sent": "Sent a message to the clinic", "appointment.created": "Booked an appointment", "appointment.updated": "Updated an appointment", "appointment.deleted": "Deleted an appointment",
  "appointment.walk_in": "Added a walk-in", "appointment.called": "Called a patient in", "consultation.created": "Wrote a consultation", "consultation.updated": "Edited a consultation", "consultation.deleted": "Deleted a consultation",
  "consultation.ai_summary": "Made an AI draft summary", "invoice.created": "Created an invoice", "invoice.payment": "Recorded a payment", "invoice.refunded": "Refunded an invoice", "invoice.deleted": "Deleted an invoice",
  "document.uploaded": "Uploaded a document", "document.deleted": "Deleted a document", "chat.cleared_own_view": "Cleared a chat from their own view",
};
const label = (a) => LABEL[a] || (a.endsWith(".purged") ? "Permanently deleted an item" : a.endsWith(".restored") ? "Restored an item" : a.startsWith("inventory.") ? "Changed inventory" : a.startsWith("ai.") ? "Confirmed an assistant action" : a);

export default function Audit() {
  const { me } = useAuth();
  const router = useRouter();
  const [role, setRole] = useState("");
  const [q, setQ] = useState("");
  const [dq, setDq] = useState("");
  useEffect(() => { if (me.role !== "owner") router.replace("/dashboard"); }, [me.role, router]);
  useEffect(() => { const t = setTimeout(() => setDq(q.trim()), 250); return () => clearTimeout(t); }, [q]);
  const params = new URLSearchParams({ limit: "200", ...(role && { role }), ...(dq && { q: dq }) }).toString();
  const list = useApi(["audit", params], `/audit?${params}`, { enabled: me.role === "owner" });
  return (
    <>
      <PageHeader title="Audit log" sub="Everything that happened in your clinic: your team and the patients who signed up with you. Other clinics never appear here." />
      <Tabs tabs={ROLES.map(([k, l]) => [k || "all", l])} value={role || "all"} onChange={(k) => setRole(k === "all" ? "" : k)} />
      <label className="sr-only" htmlFor="aq">Search actions</label><input id="aq" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search actions, e.g. deleted, message, login" className="field mb-4 max-w-md" />
      <ErrorBox error={list.error} />
      {list.isLoading ? <Skeleton /> : list.data?.length === 0 ? <Empty icon={ScrollText} title="Nothing matches" hint="Try another role or search." /> : (
        <div className="card overflow-x-auto"><table className="w-full min-w-[640px]"><thead className="border-b border-line"><tr><th className="th">When</th><th className="th">Who</th><th className="th">What happened</th></tr></thead>
          <tbody className="divide-y divide-line">{list.data.map((e) => (
            <tr key={e.id}><td className="td whitespace-nowrap text-mute">{fmtDateTime(e.at)}</td>
              <td className="td"><span className="font-medium">{e.actor}</span> <span className="ml-1 rounded-full bg-accent-soft px-2 py-0.5 text-xs font-semibold capitalize text-brand">{e.actor_role}</span></td>
              <td className="td">{label(e.action)}<span className="ml-2 font-mono text-xs text-mute">{e.action}{e.entity_id ? ` · ${String(e.entity_id).slice(0, 8)}` : ""}</span></td></tr>))}</tbody></table></div>)}
    </>
  );
}
