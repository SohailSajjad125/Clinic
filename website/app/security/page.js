import { Check, Clock } from "lucide-react";
import { Container, CtaBand, PageHero } from "@/components/ui";

export const metadata = { title: "Security", description: "How ClinicOS protects clinic and patient data, and what is still on our roadmap." };

const live = [
  ["Passwords are hashed", "Passwords are stored with bcrypt, never in plain text."],
  ["Short-lived sessions", "Access tokens expire quickly and are re-checked against the database on every request, so removing a staff member ends their access immediately."],
  ["Role-based access", "Owners, doctors, receptionists and nurses each see only what their role allows."],
  ["Clinic isolation", "Every query is scoped to your clinic. One clinic can never read another's data."],
  ["Sessions you control", "Every device is a session you can see and sign out. Refresh tokens rotate, and replaying an old one ends the session."],
  ["Sign-in protection", "Accounts lock for 15 minutes after repeated wrong passwords, and sign-in and sign-up are rate limited."],
  ["Password reset and email verification", "Single-use links that expire, and a password change signs out every other device."],
  ["Safe file uploads", "Type and content checks, a 10 MB limit, and files are only served to people allowed to see them."],
  ["Audit trail", "Staff changes and deletions are recorded with who did what and when."],
  ["Real deletion", "Items removed from Deleted history are permanently deleted from the database. The audit log keeps only an anonymous id."],
];
const planned = ["Two-factor authentication", "Encryption at rest for stored documents (depends on your hosting setup)", "Independent security review and penetration test", "Scheduled off-site backups (scripts are provided; scheduling is up to the host)", "Per-field encryption for sensitive clinical notes"];

export default function Security() {
  return (
    <>
      <PageHero title="Patient information deserves careful handling">Here is what protects your data today, and what we are still building. We would rather be accurate than impressive.</PageHero>
      <Container className="py-20">
        <h2 className="font-display text-3xl font-extrabold tracking-tight">In place</h2>
        <div className="mt-8 grid gap-5 md:grid-cols-2">
          {live.map(([t, b]) => <div key={t} className="rounded-card border border-line bg-surface p-7"><h3 className="flex items-center gap-2 font-display text-lg font-bold"><Check className="h-5 w-5 text-brand" aria-hidden="true" />{t}</h3><p className="mt-2 leading-7 text-mute">{b}</p></div>)}
        </div>
        <h2 className="mt-16 font-display text-3xl font-extrabold tracking-tight">On our roadmap</h2>
        <ul className="mt-8 grid gap-3 md:grid-cols-2">
          {planned.map((p) => <li key={p} className="flex items-center gap-3 rounded-xl border border-dashed border-line px-5 py-4 text-mute"><Clock className="h-4 w-4 shrink-0" aria-hidden="true" />{p}</li>)}
        </ul>
        <div className="mt-16 rounded-card border border-line bg-surface p-8">
          <h2 className="font-display text-2xl font-bold">Compliance</h2>
          <p className="mt-3 max-w-3xl leading-7 text-mute">Healthcare data rules differ by country. We do not claim HIPAA, GDPR or any other certification until the legal, technical and organisational requirements have been implemented and assessed. We will list each one here when it is true.</p>
        </div>
      </Container>
      <CtaBand />
    </>
  );
}
