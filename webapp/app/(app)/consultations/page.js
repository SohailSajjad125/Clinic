"use client";
import { ClipboardList } from "lucide-react";
import Link from "next/link";
import { Empty, ErrorBox, PageHeader, Skeleton } from "@/components/ui";
import { fmtDate, useApi } from "@/lib/hooks";

export default function Consultations() {
  const list = useApi(["consultations", "list"], "/consultations");
  return (
    <>
      <PageHeader title="Consultations" sub="Start a consultation from an appointment in the queue or from a patient's profile." />
      <ErrorBox error={list.error} />
      {list.isLoading ? <Skeleton /> : list.data?.length === 0 ? <Empty icon={ClipboardList} title="No consultations yet" hint="Call a patient in from Appointments, then write the notes." /> : (
        <div className="card divide-y divide-line">{list.data.map((c) => (
          <Link key={c.id} href={`/consultations/${c.id}`} className="flex flex-wrap items-center justify-between gap-2 px-5 py-4 hover:bg-bg">
            <div><p className="font-semibold">{c.patient_name}</p><p className="text-sm text-mute">{c.complaint?.slice(0, 80) || "No complaint recorded"}</p></div>
            <p className="text-sm text-mute">{fmtDate(c.created_at)} · {c.prescription.length} medicine{c.prescription.length === 1 ? "" : "s"}</p></Link>))}</div>
      )}
    </>
  );
}
