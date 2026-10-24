import ContactForm from "@/components/ContactForm";
import { Container, PageHero } from "@/components/ui";

export const metadata = { title: "Contact", description: "Book a demo, ask about pricing or get support." };

export default function Contact() {
  return (
    <>
      <PageHero title="Talk to us">Tell us about your clinic and what you'd like to improve. We read every message.</PageHero>
      <Container className="grid gap-12 py-20 lg:grid-cols-[1fr_1.4fr]">
        <div className="space-y-6">
          <div><h2 className="font-display text-xl font-bold">Book a demo</h2><p className="mt-2 leading-7 text-mute">Choose "Book a demo" in the form and tell us how many doctors you have. We'll show you the parts that matter for your clinic.</p></div>
          <div><h2 className="font-display text-xl font-bold">Already a customer?</h2><p className="mt-2 leading-7 text-mute">Choose "Support" and include your clinic name so we can find your account.</p></div>
        </div>
        <ContactForm />
      </Container>
    </>
  );
}
