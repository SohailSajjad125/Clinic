"use client";
import { Check, Circle } from "lucide-react";
import Link from "next/link";
import { PageHeader, Skeleton } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { firstName, useApi } from "@/lib/hooks";

export default function Onboarding() {
  const { me } = useAuth();
  const clinic = useApi("clinic", "/clinic");
  const services = useApi("services", "/services");
  const staff = useApi("staff", "/staff");
  const patients = useApi(["patients", "list", ""], "/patients?q=");
  if (clinic.isLoading) return <Skeleton rows={4} />;
  const hours = Object.values(clinic.data?.working_hours || {}).some(Boolean);
  const steps = [
    ["Set your working hours", "Tell patients and staff when you're open.", "/settings?tab=clinic", hours],
    ["List your services and prices", "They appear as one-tap items when you create invoices.", "/settings?tab=services", (services.data || []).length > 0],
    ["Add a doctor or receptionist", "Invite your team and choose what each role can see.", "/staff", (staff.data || []).length > 1],
    ["Add your first patient", "Everything else starts from a patient record.", "/patients?new=1", (patients.data || []).length > 0],
  ];
  return (
    <>
      <PageHeader title={`Welcome, ${firstName(me.full_name)}`} sub="Four quick steps to get your clinic ready. You can skip any of them." />
      <div className="card divide-y divide-line">{steps.map(([t, d, href, done]) => (
        <Link key={t} href={href} className="flex items-center gap-4 px-5 py-4 hover:bg-bg">
          {done ? <Check className="h-5 w-5 text-success-ink" aria-label="Done" /> : <Circle className="h-5 w-5 text-mute" aria-label="Not done" />}
          <div><p className="font-semibold">{t}</p><p className="text-sm text-mute">{d}</p></div></Link>))}</div>
      <Link href="/dashboard" className="btn btn-primary mt-6">Go to dashboard</Link>
    </>
  );
}
