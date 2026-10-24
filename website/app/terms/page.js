import { Container } from "@/components/ui";

export const metadata = { title: "Terms of service" };

export default function Terms() {
  return (
    <Container className="max-w-3xl py-16">
      <h1 className="font-display text-4xl font-extrabold tracking-tight">Terms of service</h1>
      <p className="mt-3 text-sm text-mute">Last updated 1 October 2026. This is a working draft and must be reviewed by a qualified lawyer before launch.</p>
      <div className="prose-c mt-10">
        <h2>Using ClinicOS</h2>
        <p>ClinicOS is software for managing a clinic. You are responsible for the accuracy of the information you enter and for using the product in line with the laws and professional rules that apply to you.</p>
        <h2>Not medical advice</h2>
        <p>ClinicOS does not diagnose, treat or prescribe. Any text produced by the AI assistant is a draft that a qualified person must review before relying on it.</p>
        <h2>Accounts</h2>
        <p>Keep your credentials confidential. The clinic owner is responsible for the people given access and for removing access when it is no longer needed.</p>
        <h2>Your data</h2>
        <p>You keep ownership of the data you enter. You can export it and delete it. Items permanently removed from Deleted history cannot be recovered.</p>
        <h2>Changes</h2>
        <p>We may update these terms and will tell customers about material changes before they apply.</p>
      </div>
    </Container>
  );
}
