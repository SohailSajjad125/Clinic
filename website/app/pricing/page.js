import Faq from "@/components/Faq";
import PricingTable from "@/components/PricingTable";
import { Container, CtaBand, PageHero } from "@/components/ui";

export const metadata = { title: "Pricing", description: "Simple plans for solo practitioners, clinics and multi-doctor practices. Start free." };

export default function Pricing() {
  return (
    <>
      <PageHero title="Simple pricing that grows with your clinic">Start free. Upgrade when you add doctors or need the live queue, portal and assistant.</PageHero>
      <Container className="py-20"><PricingTable />
        <p className="mt-8 text-center text-sm text-mute">Prices are in Pakistani rupees and exclude applicable taxes.</p>
      </Container>
      <Container className="pb-24"><h2 className="mb-6 font-display text-3xl font-extrabold tracking-tight">Common questions</h2><Faq limit={4} /></Container>
      <CtaBand />
    </>
  );
}
