import { Check } from "lucide-react";
import { Container, CtaBand, FeatureIcon, PageHero } from "@/components/ui";
import { features } from "@/lib/content";

export const metadata = { title: "Features", description: "Patient records, appointments, consultations, prescriptions, billing, real-time chat, analytics and an AI assistant." };

export default function Features() {
  return (
    <>
      <PageHero title="Everything a clinic runs on, in one place">From the moment a patient books to the moment the invoice is paid, every step lives in the same workspace.</PageHero>
      <Container className="divide-y divide-line py-8">
        {features.map((f) => (
          <section key={f.title} className="grid gap-8 py-14 md:grid-cols-[1fr_1.2fr]">
            <div>
              <span className="grid h-12 w-12 place-items-center rounded-xl bg-accent-soft text-brand"><FeatureIcon name={f.icon} className="h-6 w-6" /></span>
              <h2 className="mt-5 font-display text-3xl font-extrabold tracking-tight">{f.title}</h2>
              <p className="mt-3 max-w-md leading-7 text-mute">{f.body}</p>
            </div>
            <ul className="space-y-3 self-center">
              {f.points.map((p) => <li key={p} className="flex gap-3 rounded-xl border border-line bg-surface px-5 py-4"><Check className="mt-0.5 h-5 w-5 shrink-0 text-brand" aria-hidden="true" />{p}</li>)}
            </ul>
          </section>
        ))}
      </Container>
      <CtaBand />
    </>
  );
}
