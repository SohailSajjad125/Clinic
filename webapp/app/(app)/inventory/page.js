"use client";
import { Minus, Package, Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import { Modal, useConfirm } from "@/components/Modal";
import { Empty, ErrorBox, Field, PageHeader, Skeleton } from "@/components/ui";
import { del, post } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { money, useAct, useApi } from "@/lib/hooks";

export default function Inventory() {
  const { me } = useAuth();
  const canWrite = ["owner", "doctor", "receptionist"].includes(me.role);
  const [add, setAdd] = useState(false);
  const [adj, setAdj] = useState(null);
  const act = useAct();
  const confirm = useConfirm();
  const list = useApi("inventory", "/inventory");
  const num = (f, k) => Number(f[k]) || 0;
  async function create(e) {
    e.preventDefault();
    const f = Object.fromEntries(new FormData(e.currentTarget));
    if (await act(() => post("/inventory", { name: f.name, unit: f.unit || "pcs", quantity: num(f, "quantity"), reorder_level: num(f, "reorder_level"), unit_price: num(f, "unit_price") }), { ok: "Item added", invalidate: ["inventory"] })) setAdd(false);
  }
  async function adjust(e) {
    e.preventDefault();
    const f = Object.fromEntries(new FormData(e.currentTarget));
    const delta = (adj.sign === "-" ? -1 : 1) * Math.abs(num(f, "delta"));
    if (await act(() => post(`/inventory/${adj.item.id}/adjust`, { delta, reason: f.reason || "" }), { ok: "Stock updated", invalidate: ["inventory"] })) setAdj(null);
  }
  async function remove(i) {
    if (await confirm({ title: `Delete ${i.name}?`, body: "It moves to Deleted history, where the owner can restore it or remove it permanently.", action: "Delete", danger: true })) act(() => del(`/inventory/${i.id}`), { ok: "Moved to Deleted history", invalidate: ["inventory", "trash"] });
  }
  return (
    <>
      <PageHeader title="Inventory" sub="Medicines and supplies. The owner is alerted when stock runs low.">{canWrite && <button className="btn btn-primary" onClick={() => setAdd(true)}><Plus className="h-4 w-4" />Add item</button>}</PageHeader>
      <ErrorBox error={list.error} />
      {list.isLoading ? <Skeleton /> : list.data.length === 0 ? <Empty icon={Package} title="No stock items yet" hint="Track medicines and supplies and get low-stock alerts.">{canWrite && <button className="btn btn-primary" onClick={() => setAdd(true)}>Add item</button>}</Empty> : (
        <div className="card overflow-x-auto"><table className="w-full min-w-[620px]"><thead className="border-b border-line"><tr><th className="th">Item</th><th className="th">In stock</th><th className="th">Reorder at</th><th className="th">Unit price</th><th className="th" /></tr></thead>
          <tbody className="divide-y divide-line">{list.data.map((i) => (
            <tr key={i.id}><td className="td font-semibold">{i.name}</td>
              <td className="td"><span className={i.low ? "font-semibold text-danger-ink" : ""}>{i.quantity} {i.unit}</span>{i.low && <span className="ml-2 rounded-full bg-danger/15 px-2 py-0.5 text-xs font-semibold text-danger-ink">Low</span>}</td>
              <td className="td text-mute">{i.reorder_level}</td><td className="td text-mute">{money(i.unit_price)}</td>
              <td className="td"><div className="flex justify-end gap-1">{canWrite && <><button className="btn btn-outline btn-sm" aria-label={`Add stock to ${i.name}`} onClick={() => setAdj({ item: i, sign: "+" })}><Plus className="h-3.5 w-3.5" /></button>
                <button className="btn btn-outline btn-sm" aria-label={`Use stock of ${i.name}`} onClick={() => setAdj({ item: i, sign: "-" })}><Minus className="h-3.5 w-3.5" /></button>
                <button onClick={() => remove(i)} aria-label={`Delete ${i.name}`} className="rounded-lg p-2 text-mute hover:bg-danger/10 hover:text-danger-ink"><Trash2 className="h-4 w-4" /></button></>}</div></td></tr>))}</tbody></table></div>)}
      <Modal open={add} onClose={() => setAdd(false)} title="Add inventory item">
        <form onSubmit={create} className="grid grid-cols-2 gap-4">
          <div className="col-span-2"><Field label="Name"><input name="name" required className="field" /></Field></div>
          <Field label="Unit"><input name="unit" defaultValue="pcs" className="field" /></Field><Field label="Quantity"><input name="quantity" type="number" min={0} defaultValue={0} className="field" /></Field>
          <Field label="Reorder at"><input name="reorder_level" type="number" min={0} defaultValue={0} className="field" /></Field><Field label="Unit price (PKR)"><input name="unit_price" type="number" min={0} defaultValue={0} className="field" /></Field>
          <div className="col-span-2 flex justify-end gap-3"><button type="button" className="btn btn-outline" onClick={() => setAdd(false)}>Cancel</button><button className="btn btn-primary">Add</button></div>
        </form>
      </Modal>
      <Modal open={!!adj} onClose={() => setAdj(null)} title={adj ? `${adj.sign === "+" ? "Add stock" : "Use stock"}: ${adj.item.name}` : ""}>
        {adj && <form onSubmit={adjust} className="space-y-4"><Field label={`Quantity (${adj.item.unit})`}><input name="delta" type="number" min={1} required defaultValue={1} className="field" /></Field><Field label="Reason (optional)"><input name="reason" className="field" /></Field>
          <div className="flex justify-end gap-3"><button type="button" className="btn btn-outline" onClick={() => setAdj(null)}>Cancel</button><button className="btn btn-primary">Save</button></div></form>}
      </Modal>
    </>
  );
}
