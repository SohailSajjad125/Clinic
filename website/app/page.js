import { ArrowRight, Lock, ShieldCheck } from "lucide-react";
import Link from "next/link";
import AssistantDemo from "@/components/AssistantDemo";
import Faq from "@/components/Faq";
import HeroPreview from "@/components/HeroPreview";
import Reveal from "@/components/Reveal";
import { Container, CtaBand, FeatureIcon } from "@/components/ui";
import { APP_URL, features } from "@/lib/content";

const steps = [
  ["Create your clinic", "Sign up, name your clinic and choose its type. It takes a few minutes."],
  ["Add your team and services", "Invite doctors and reception, set working hours, and list what you charge for."],
  ["See your first patient", "Register, book, consult, prescribe and bill without leaving the workspace."],
];
const bento = [
  ["CalendarClock", "md:col-span-2"], ["Users", ""], ["Stethoscope", ""], ["Receipt", "md:col-span-2"], ["MessagesSquare", ""], ["BarChart3", ""],
].map(([icon, span]) => ({ ...features.find((f) => f.icon === icon), span }));

export default function Home() {
  return (
    <>
      <section className="hero-glow overflow-hidden">
        <Container className="grid items-center gap-14 py-20 md:py-28 lg:grid-cols-[1.05fr_1fr]">
          <div>
            <h1 className="font-display text-5xl font-extrabold leading-[1.05] tracking-tight md:text-6xl lg:text-7xl">Your clinic. One intelligent workspace.</h1>
            <p className="mt-6 max-w-xl text-lg leading-8 text-mute">Manage patients, appointments, records, prescriptions and billing from one secure platform, and let an assistant handle the admin.</p>
            <div className="mt-9 flex flex-wrap gap-3">
              <a href={`${APP_URL}/signup`} className="btn btn-primary">Start free <ArrowRight className="h-4 w-4" /></a>
              <a href="#how" className="btn btn-outline">See how it works</a>
            </div>
            <p className="mt-5 text-sm text-mute">Built for independent clinics in Pakistan and beyond.</p>
          </div>
          <div className="flex justify-center lg:justify-end"><HeroPreview /></div>
        </Container>
      </section>

      <section className="border-b border-line bg-surface">
        <Container className="py-8"><p className="max-w-3xl text-lg font-medium leading-8">Replaces the paper register, the WhatsApp thread, the Excel sheet and the separate billing app, so everyone works from one source of truth.</p></Container>
      </section>

      <section className="py-24">
        <Container>
          <Reveal><h2 className="max-w-2xl font-display text-3xl font-extrabold tracking-tight md:text-5xl">Everything the front desk and the doctor need</h2></Reveal>
          <div className="mt-12 grid gap-5 md:grid-cols-4">
            {bento.map((f, i) => (
              <Reveal key={f.title} delay={i * 0.05} className={f.span || "md:col-span-1"}>
                <div className="h-full rounded-card border border-line bg-surface p-7 transition-transform duration-300 hover:-translate-y-1">
                  <span className="grid h-11 w-11 place-items-center rounded-xl bg-accent-soft text-brand"><FeatureIcon name={f.icon} /></span>
                  <h3 className="mt-5 font-display text-xl font-bold">{f.title}</h3>
                  <p className="mt-2 leading-7 text-mute">{f.body}</p>
                </div>
              </Reveal>
            ))}
          </div>
          <Link href="/features" className="mt-8 inline-flex items-center gap-2 font-semibold text-brand">See every feature <ArrowRight className="h-4 w-4" /></Link>
        </Container>
      </section>

      <section id="how" className="scroll-mt-20 border-y border-line bg-surface py-24">
        <Container>
          <h2 className="max-w-2xl font-display text-3xl font-extrabold tracking-tight md:text-5xl">From sign-up to first patient in an afternoon</h2>
          <ol className="mt-12 grid gap-10 md:grid-cols-3">
            {steps.map(([t, b], i) => (
              <li key={t}><span className="font-display text-5xl font-extrabold text-brand">{i + 1}</span><h3 className="mt-3 font-display text-xl font-bold">{t}</h3><p className="mt-2 leading-7 text-mute">{b}</p></li>
            ))}
          </ol>
        </Container>
      </section>

      <section className="py-24">
        <Container className="grid items-center gap-14 lg:grid-cols-2">
          <div>
            <h2 className="font-display text-3xl font-extrabold tracking-tight md:text-5xl">An assistant that actually does things</h2>
            <p className="mt-5 text-lg leading-8 text-mute">Ask how something works, or tell it what to do. It uses the same permissions as you, shows what it is about to change, and waits for your confirmation.</p>
            <ul className="mt-6 space-y-3 text-mute">
              <li className="flex gap-3"><ShieldCheck className="mt-1 h-5 w-5 shrink-0 text-brand" aria-hidden="true" />Never diagnoses or prescribes. Clinical text it writes is marked as a draft.</li>
              <li className="flex gap-3"><Lock className="mt-1 h-5 w-5 shrink-0 text-brand" aria-hidden="true" />Every action it takes is recorded in the audit log.</li>
            </ul>
          </div>
          <AssistantDemo />
        </Container>
      </section>

      <section className="border-t border-line bg-surface py-24">
        <Container className="grid gap-12 lg:grid-cols-[1fr_1.4fr]">
          <div>
            <h2 className="font-display text-3xl font-extrabold tracking-tight md:text-4xl">Questions clinics ask us</h2>
            <Link href="/faq" className="mt-6 inline-flex items-center gap-2 font-semibold text-brand">All questions <ArrowRight className="h-4 w-4" /></Link>
          </div>
          <Faq limit={5} />
        </Container>
      </section>
      <CtaBand />
    </>
  );
}
