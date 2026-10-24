import { Container, CtaBand, PageHero } from "@/components/ui";
import { solutions } from "@/lib/content";

export const metadata = { title: "Solutions", description: "ClinicOS for general physicians, dentists, physiotherapists, dermatologists, multi-doctor clinics and diagnostic centres." };

export default function Solutions() {
  return (
    <>
      <PageHero title="Built around how different clinics really work">The same workspace adapts to a single-doctor practice or a busy multi-doctor clinic.</PageHero>
      <Container className="grid gap-5 py-20 md:grid-cols-2">
        {solutions.map((s) => (
          <article key={s.title} className="rounded-card border border-line bg-surface p-8">
            <h2 className="font-display text-2xl font-bold">{s.title}</h2>
            <p className="mt-4 text-sm font-semibold text-mute">The challenge</p><p className="mt-1 leading-7">{s.pain}</p>
            <p className="mt-4 text-sm font-semibold text-brand">How ClinicOS helps</p><p className="mt-1 leading-7 text-mute">{s.fix}</p>
          </article>
        ))}
      </Container>
      <CtaBand />
    </>
  );
}
