import Link from "next/link";
import Logo from "./Logo";
import NewsletterForm from "./NewsletterForm";
import { APP_URL } from "@/lib/content";

const cols = [
  { title: "Product", links: [["/features", "Features"], ["/solutions", "Solutions"], ["/pricing", "Pricing"], ["/security", "Security"]] },
  { title: "Company", links: [["/about", "About"], ["/resources", "Resources"], ["/faq", "FAQ"], ["/contact", "Contact"]] },
  { title: "Legal", links: [["/privacy", "Privacy policy"], ["/terms", "Terms of service"]] },
];

export default function Footer() {
  return (
    <footer className="border-t border-line bg-surface">
      <div className="mx-auto grid max-w-6xl gap-12 px-5 py-14 sm:px-8 lg:grid-cols-[1.4fr_2fr]">
        <div>
          <Logo />
          <p className="mt-4 max-w-sm text-sm leading-6 text-mute">The operating system for modern clinics. Appointments, records, prescriptions and billing in one secure workspace.</p>
          <div className="mt-6 max-w-sm"><p className="mb-2 text-sm font-semibold">Clinic management tips, once a month</p><NewsletterForm /></div>
        </div>
        <div className="grid grid-cols-2 gap-8 sm:grid-cols-4">
          {cols.map((c) => (
            <div key={c.title}>
              <p className="mb-3 text-sm font-semibold">{c.title}</p>
              <ul className="space-y-2 text-sm text-mute">{c.links.map(([h, l]) => <li key={h}><Link href={h} className="hover:text-brand">{l}</Link></li>)}</ul>
            </div>
          ))}
          <div>
            <p className="mb-3 text-sm font-semibold">Get started</p>
            <ul className="space-y-2 text-sm text-mute">
              <li><a href={`${APP_URL}/login`} className="hover:text-brand">Clinic log in</a></li>
              <li><a href={`${APP_URL}/signup`} className="hover:text-brand">Clinic sign up</a></li>
              <li><a href={`${APP_URL}/patient/login`} className="hover:text-brand">Patient log in</a></li>
              <li><a href={`${APP_URL}/patient/signup`} className="hover:text-brand">Patient sign up</a></li>
            </ul>
          </div>
        </div>
      </div>
      <div className="border-t border-line">
        <p className="mx-auto max-w-6xl px-5 py-6 text-xs leading-5 text-mute sm:px-8">© 2026 ClinicOS. ClinicOS is clinic management software and does not provide medical advice or diagnosis.</p>
      </div>
    </footer>
  );
}
