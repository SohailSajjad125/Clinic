import { Container, CtaBand, PageHero } from "@/components/ui";

export const metadata = { title: "About", description: "Why we are building ClinicOS and the principles behind it." };
const principles = [
  ["Clinicians decide", "Software supports the clinician. It never makes clinical decisions for them."],
  ["Honest by default", "We state what the product does today, what it doesn't, and what is still planned."],
  ["Mistakes are recoverable", "Deleting something by accident shouldn't be a disaster, and deleting on purpose should really delete."],
  ["Calm interfaces", "A busy front desk needs clear screens, not clutter or tricks."],
];

export default function About() {
  return (
    <>
      <PageHero title="Clinics deserve better tools than a paper register and a WhatsApp group">ClinicOS started from a simple observation: many independent clinics run on disconnected tools, and the people running them are too busy to fix it.</PageHero>
      <Container className="max-w-4xl py-20">
        <div className="prose-c text-lg">
          <p>We are building one workspace where patients, appointments, records, prescriptions and billing live together, and where an assistant can take over repetitive administration safely.</p>
          <p>We are starting with independent clinics in Pakistan, where the gap between what clinics need and what is available is wide, and plan to grow region by region from there.</p>
        </div>
        <h2 className="mt-12 font-display text-3xl font-extrabold tracking-tight">What we believe</h2>
        <div className="mt-8 grid gap-5 md:grid-cols-2">
          {principles.map(([t, b]) => <div key={t} className="rounded-card border border-line bg-surface p-7"><h3 className="font-display text-lg font-bold">{t}</h3><p className="mt-2 leading-7 text-mute">{b}</p></div>)}
        </div>
      </Container>
      <CtaBand />
    </>
  );
}
