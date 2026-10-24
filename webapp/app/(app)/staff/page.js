"use client";
import { Plus, Stethoscope, Trash2 } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { DoctorForm, DoctorCard } from "@/components/Doctor";
import { Modal, useConfirm } from "@/components/Modal";
import { ErrorBox, Field, PageHeader, Skeleton } from "@/components/ui";
import { del, patch, post } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useAct, useApi } from "@/lib/hooks";

export default function Staff() {
  const { me } = useAuth();
  const owner = me.role === "owner";
  const [open, setOpen] = useState(false);
  const [role, setRole] = useState("doctor");
  const [edit, setEdit] = useState(null);
  const act = useAct();
  const confirm = useConfirm();
  const list = useApi("staff", "/staff");
  const docs = useApi("doctors", "/doctors");
  async function add(e) {
    e.preventDefault();
    const f = Object.fromEntries(new FormData(e.currentTarget));
    const body = { email: f.email.trim(), full_name: f.full_name, role: f.role, password: f.password };
    if (f.role === "doctor") body.profile = DoctorForm.read(e.currentTarget);
    if (await act(() => post("/staff", body), { ok: "Team member added. They choose their own password at first login.", invalidate: ["staff", "doctors"] })) setOpen(false);
  }
  async function remove(s) {
    if (await confirm({ title: `Remove ${s.full_name}?`, body: "They lose access immediately. They move to Deleted history, where you can restore or permanently remove them.", action: "Remove", danger: true }))
      act(() => del(`/staff/${s.member_id}`), { ok: "Moved to Deleted history", invalidate: ["staff", "doctors", "trash"] });
  }
  async function saveProfile(e) {
    e.preventDefault();
    if (await act(() => patch(`/staff/${edit.member_id}/profile`, DoctorForm.read(e.currentTarget)), { ok: "Doctor profile updated", invalidate: ["doctors"] })) setEdit(null);
  }
  const doctors = docs.data || [];
  return (
    <>
      <PageHeader title="Team & doctors" sub="Doctors, reception and nurses who use this clinic's workspace.">
        {owner && <Link href="/trash" className="btn btn-outline">Deleted history</Link>}{owner && <button className="btn btn-primary" onClick={() => { setRole("doctor"); setOpen(true); }}><Plus className="h-4 w-4" />Add team member</button>}</PageHeader>
      <ErrorBox error={list.error} />
      <h2 className="mb-3 flex items-center gap-2 font-display text-xl font-bold"><Stethoscope className="h-5 w-5 text-brand" aria-hidden="true" />Doctors</h2>
      {docs.isLoading ? <Skeleton rows={2} /> : doctors.length === 0 ? <p className="mb-8 text-mute">No doctors yet. {owner ? "Add one to start taking appointments." : ""}</p> : (
        <div className="mb-8 grid gap-4 md:grid-cols-2">{doctors.map((d) => <DoctorCard key={d.member_id} d={d} onEdit={owner ? () => setEdit(d) : undefined} />)}</div>)}
      <h2 className="mb-3 font-display text-xl font-bold">Everyone</h2>
      {list.isLoading ? <Skeleton /> : (
        <div className="card divide-y divide-line">{list.data.map((s) => (
          <div key={s.member_id} className="flex items-center justify-between gap-3 px-5 py-4">
            <div className="flex items-center gap-4"><span className="grid h-10 w-10 place-items-center rounded-full bg-accent-soft font-bold text-brand">{s.full_name[0]}</span>
              <div><p className="font-semibold">{s.full_name}{s.member_id === me.member_id && <span className="ml-2 text-xs text-mute">(you)</span>}</p><p className="text-sm text-mute">{s.email}</p></div></div>
            <div className="flex items-center gap-3">{owner && s.role === "receptionist" && <label className="hidden items-center gap-1.5 text-xs text-mute sm:flex"><input type="checkbox" checked={s.can_view_clinical} onChange={(e) => act(() => patch(`/staff/${s.member_id}/permissions`, { can_view_clinical: e.target.checked }), { ok: "Permission updated", invalidate: ["staff"] })} />Can view clinical notes</label>}
              <span className="rounded-full bg-bg px-3 py-1 text-xs font-semibold capitalize">{s.role}</span>
              {owner && s.role !== "owner" && <button onClick={() => remove(s)} aria-label={`Remove ${s.full_name}`} className="rounded-lg p-2 text-mute hover:bg-danger/10 hover:text-danger-ink"><Trash2 className="h-4 w-4" /></button>}</div></div>))}</div>)}
      <Modal open={open} onClose={() => setOpen(false)} title="Add team member" wide>
        <form onSubmit={add} className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2"><Field label="Full name"><input name="full_name" required minLength={2} className="field" /></Field><Field label="Email"><input name="email" type="email" required className="field" /></Field>
            <Field label="Role"><select name="role" value={role} onChange={(e) => setRole(e.target.value)} className="field"><option value="doctor">Doctor</option><option value="receptionist">Receptionist</option><option value="nurse">Nurse</option></select></Field>
            <Field label="Temporary password" hint="At least 8 characters. They must change it at first login."><input name="password" type="text" required minLength={8} autoComplete="off" className="field" /></Field></div>
          {role === "doctor" && <DoctorForm />}
          <div className="flex justify-end gap-3"><button type="button" className="btn btn-outline" onClick={() => setOpen(false)}>Cancel</button><button className="btn btn-primary">Add</button></div>
        </form>
      </Modal>
      <Modal open={!!edit} onClose={() => setEdit(null)} title={edit ? `Edit ${edit.full_name}` : ""} wide>
        {edit && <form onSubmit={saveProfile} className="space-y-4"><DoctorForm initial={edit.profile} /><div className="flex justify-end gap-3"><button type="button" className="btn btn-outline" onClick={() => setEdit(null)}>Cancel</button><button className="btn btn-primary">Save profile</button></div></form>}
      </Modal>
    </>
  );
}
