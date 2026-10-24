"use client";
import { Plus, Receipt, Trash2 } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { Modal, useConfirm } from "@/components/Modal";
import { Badge, Empty, ErrorBox, Field, PageHeader, Skeleton } from "@/components/ui";
import { del, openFile, post } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { fmtDate, money, useAct, useApi } from "@/lib/hooks";

const line = () => ({ description: "", qty: 1, price: 0 });

function InvoiceModal({ open, onClose, patientId }) {
  const act = useAct();
  const patients = useApi(["patients", "all"], "/patients?limit=500", { enabled: open });
  const services = useApi("services", "/services", { enabled: open });
  const [items, setItems] = useState([line()]);
  const [discount, setDiscount] = useState(0);
  const [tax, setTax] = useState(0);
  useEffect(() => { if (open) { setItems([line()]); setDiscount(0); setTax(0); } }, [open]);
  const sub = items.reduce((s, i) => s + (Number(i.qty) || 0) * (Number(i.price) || 0), 0);
  const total = sub - (Number(discount) || 0) + (Number(tax) || 0);
  const set = (i, k, v) => setItems((l) => l.map((x, j) => (j === i ? { ...x, [k]: v } : x)));
  async function submit(e) {
    e.preventDefault();
    const f = Object.fromEntries(new FormData(e.currentTarget));
    const body = { patient_id: f.patient_id, items: items.filter((i) => i.description.trim()).map((i) => ({ description: i.description.trim(), qty: Number(i.qty) || 1, price: Number(i.price) || 0 })), discount: Number(discount) || 0, tax: Number(tax) || 0 };
    if (!body.items.length) return;
    if (await act(() => post("/invoices", body), { ok: "Invoice created", invalidate: ["invoices"] })) onClose();
  }
  return (
    <Modal open={open} onClose={onClose} title="New invoice" wide>
      <form onSubmit={submit} className="space-y-4">
        <Field label="Patient"><select name="patient_id" required defaultValue={patientId || ""} className="field"><option value="" disabled>Choose a patient</option>{(patients.data || []).map((p) => <option key={p.id} value={p.id}>{p.full_name}</option>)}</select></Field>
        <div className="space-y-2"><p className="text-sm font-medium">Items</p>
          {items.map((it, i) => (
            <div key={i} className="grid grid-cols-[1fr_70px_110px_auto] gap-2">
              <input aria-label="Description" placeholder="Consultation, lab, medicine…" value={it.description} onChange={(e) => set(i, "description", e.target.value)} className="field" />
              <input aria-label="Quantity" type="number" min={1} value={it.qty} onChange={(e) => set(i, "qty", e.target.value)} className="field" />
              <input aria-label="Price" type="number" min={0} value={it.price} onChange={(e) => set(i, "price", e.target.value)} className="field" />
              <button type="button" aria-label="Remove item" disabled={items.length === 1} onClick={() => setItems(items.filter((_, j) => j !== i))} className="rounded-lg px-2 text-mute hover:text-danger-ink disabled:opacity-30"><Trash2 className="h-4 w-4" /></button></div>))}
          <div className="flex flex-wrap gap-2"><button type="button" className="btn btn-outline btn-sm" onClick={() => setItems([...items, line()])}><Plus className="h-4 w-4" />Add item</button>
            {(services.data || []).slice(0, 8).map((sv) => <button key={sv.id} type="button" className="rounded-full border border-line bg-surface px-3 py-1 text-xs hover:border-brand" onClick={() => setItems((l) => [...l.filter((x) => x.description.trim() || Number(x.price)), { description: sv.name, qty: 1, price: sv.price }])}>+ {sv.name} · {money(sv.price)}</button>)}</div></div>
        <div className="grid grid-cols-2 gap-4"><Field label="Discount (PKR)"><input type="number" min={0} value={discount} onChange={(e) => setDiscount(e.target.value)} className="field" /></Field><Field label="Tax (PKR)"><input type="number" min={0} value={tax} onChange={(e) => setTax(e.target.value)} className="field" /></Field></div>
        <div className="flex items-center justify-between rounded-xl bg-bg p-4"><span className="text-mute">Total</span><span className="font-display text-2xl font-extrabold">{money(total)}</span></div>
        {total < 0 && <p role="alert" className="text-sm text-danger-ink">The discount can't be more than the subtotal.</p>}
        <div className="flex justify-end gap-3"><button type="button" className="btn btn-outline" onClick={onClose}>Cancel</button><button className="btn btn-primary" disabled={total < 0}>Create invoice</button></div>
      </form>
    </Modal>
  );
}

function Inner() {
  const { me } = useAuth();
  const sp = useSearchParams();
  const pre = sp.get("patient");
  const [open, setOpen] = useState(false);
  const [pay, setPay] = useState(null);
  const act = useAct();
  const confirm = useConfirm();
  useEffect(() => { if ((pre || sp.get("new") === "1") && ["owner", "receptionist"].includes(me.role)) setOpen(true); }, [pre, sp, me.role]);
  const list = useApi(["invoices", "list"], "/invoices");
  const canWrite = ["owner", "receptionist"].includes(me.role);

  async function addPayment(e) {
    e.preventDefault();
    const fd = new FormData(e.currentTarget); const amount = Number(fd.get("amount"));
    if (await act(() => post(`/invoices/${pay.id}/payments`, { amount, method: fd.get("method") }), { ok: "Payment recorded", invalidate: ["invoices"] })) setPay(null);
  }
  async function refund(i) {
    if (await confirm({ title: `Refund invoice #${i.number}?`, body: `${money(i.paid)} will be marked as refunded. This can't be undone.`, action: "Refund", danger: true })) act(() => post(`/invoices/${i.id}/refund`), { ok: "Invoice refunded", invalidate: ["invoices"] });
  }
  async function remove(i) {
    if (await confirm({ title: `Delete invoice #${i.number}?`, body: "It moves to Deleted history, where the owner can restore it or remove it permanently.", action: "Delete", danger: true })) act(() => del(`/invoices/${i.id}`), { ok: "Moved to Deleted history", invalidate: ["invoices"] });
  }
  return (
    <>
      <PageHeader title="Billing" sub="Invoices, payments and refunds.">{canWrite && <button className="btn btn-primary" onClick={() => setOpen(true)}><Plus className="h-4 w-4" />New invoice</button>}</PageHeader>
      <ErrorBox error={list.error} />
      {list.isLoading ? <Skeleton /> : list.data?.length === 0 ? <Empty icon={Receipt} title="No invoices yet" hint="Create an invoice after a visit.">{canWrite && <button className="btn btn-primary" onClick={() => setOpen(true)}>New invoice</button>}</Empty> : (
        <div className="card overflow-x-auto"><table className="w-full min-w-[680px]"><thead className="border-b border-line"><tr><th className="th">#</th><th className="th">Patient</th><th className="th">Date</th><th className="th">Total</th><th className="th">Paid</th><th className="th">Status</th><th className="th" /></tr></thead>
          <tbody className="divide-y divide-line">{list.data.map((i) => (
            <tr key={i.id}><td className="td font-mono">{i.number}</td><td className="td font-semibold">{i.patient_name}</td><td className="td text-mute">{fmtDate(i.created_at)}</td><td className="td">{money(i.total)}</td><td className="td">{money(i.paid)}</td><td className="td"><Badge s={i.status} /></td>
              <td className="td"><div className="flex justify-end gap-2"><button className="btn btn-outline btn-sm" onClick={() => act(() => openFile(`/invoices/${i.id}/receipt.pdf`))}>PDF</button>{canWrite && ["pending", "partial"].includes(i.status) && <button className="btn btn-primary btn-sm" onClick={() => setPay(i)}>Add payment</button>}
                {canWrite && i.paid > 0 && i.status !== "refunded" && <button className="btn btn-outline btn-sm" onClick={() => refund(i)}>Refund</button>}
                {canWrite && <button onClick={() => remove(i)} aria-label={`Delete invoice ${i.number}`} className="rounded-lg p-2 text-mute hover:bg-danger/10 hover:text-danger-ink"><Trash2 className="h-4 w-4" /></button>}</div></td></tr>))}</tbody></table></div>
      )}
      <InvoiceModal open={open} onClose={() => setOpen(false)} patientId={pre} />
      <Modal open={!!pay} onClose={() => setPay(null)} title={`Payment for invoice #${pay?.number}`}>
        {pay && <form onSubmit={addPayment} className="space-y-4"><p className="text-mute">Balance due: <b className="text-ink">{money(pay.total - pay.paid)}</b></p>
          <Field label="Amount (PKR)"><input name="amount" type="number" min={1} max={pay.total - pay.paid} defaultValue={pay.total - pay.paid} required className="field" /></Field>
          <Field label="Method"><select name="method" className="field"><option value="cash">Cash</option><option value="card">Card</option><option value="bank">Bank transfer</option><option value="online">Online (recorded)</option></select></Field>
          <div className="flex justify-end gap-3"><button type="button" className="btn btn-outline" onClick={() => setPay(null)}>Cancel</button><button className="btn btn-primary">Record payment</button></div></form>}
      </Modal>
    </>
  );
}
export default function Billing() { return <Suspense fallback={<Skeleton />}><Inner /></Suspense>; }
