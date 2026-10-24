import { ArrowRight, BarChart3, Bot, CalendarClock, FileText, HeartPulse, MessagesSquare, Package, Pill, Receipt, Stethoscope, Trash2, Users } from "lucide-react";
import { APP_URL } from "@/lib/content";

const icons = { FileText, HeartPulse, Package, Users, CalendarClock, Stethoscope, Pill, Receipt, MessagesSquare, BarChart3, Bot, Trash2 };

export function FeatureIcon({ name, className = "h-5 w-5" }) {
  const I = icons[name] || Users;
  return <I className={className} aria-hidden="true" />;
}

export function Container({ children, className = "" }) {
  return <div className={`mx-auto w-full max-w-6xl px-5 sm:px-8 ${className}`}>{children}</div>;
}

export function PageHero({ title, children }) {
  return (
    <section className="hero-glow">
      <Container className="py-20 md:py-28">
        <h1 className="max-w-3xl font-display text-4xl font-extrabold leading-[1.08] tracking-tight md:text-6xl">{title}</h1>
        <p className="mt-6 max-w-2xl text-lg leading-8 text-mute">{children}</p>
      </Container>
    </section>
  );
}

export function CtaBand() {
  return (
    <section className="hero-glow">
      <Container className="flex flex-col items-start justify-between gap-8 py-16 md:flex-row md:items-center">
        <div>
          <h2 className="font-display text-3xl font-extrabold tracking-tight md:text-4xl">Ready to run a calmer clinic?</h2>
          <p className="mt-3 max-w-lg text-mute">Create your clinic in a few minutes. No card needed to start.</p>
        </div>
        <div className="flex flex-wrap gap-3">
          <a href={`${APP_URL}/signup`} className="btn btn-primary">Start free <ArrowRight className="h-4 w-4" /></a>
          <a href="/contact" className="btn btn-outline">Book a demo</a><a href={`${APP_URL}/patient/signup`} className="btn btn-outline">I'm a patient</a>
        </div>
      </Container>
    </section>
  );
}
