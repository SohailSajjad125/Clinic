import { Container } from "@/components/ui";

export const metadata = { title: "Privacy policy" };

export default function Privacy() {
  return (
    <Container className="max-w-3xl py-16">
      <h1 className="font-display text-4xl font-extrabold tracking-tight">Privacy policy</h1>
      <p className="mt-3 text-sm text-mute">Last updated 1 October 2026. This is a working draft and must be reviewed by a qualified lawyer before launch.</p>
      <div className="prose-c mt-10">
        <h2>What this website collects</h2>
        <p>If you use the contact form we store the name, email address, optional clinic name and phone number, topic and message you submit, so that we can reply. If you subscribe to the newsletter we store your email address.</p>
        <h2>How we use it</h2>
        <p>We use contact details only to respond to you and, for subscribers, to send the newsletter. We do not sell personal information.</p>
        <h2>Cookies and storage</h2>
        <p>This website stores one preference in your browser (light or dark theme). We do not use advertising cookies.</p>
        <h2>Clinic and patient data</h2>
        <p>Data entered into the ClinicOS application belongs to the clinic that entered it. The clinic is responsible for how it uses that data, and we process it on the clinic's behalf. A separate data processing agreement will apply to customers.</p>
        <h2>Your choices</h2>
        <p>You can ask us to delete your contact message or unsubscribe at any time through the contact page.</p>
      </div>
    </Container>
  );
}
