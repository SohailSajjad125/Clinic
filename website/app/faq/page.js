import Faq from "@/components/Faq";
import { Container, PageHero } from "@/components/ui";
import { faqs } from "@/lib/content";

export const metadata = { title: "FAQ", description: "Answers to common questions about ClinicOS." };

export default function FaqPage() {
  const ld = { "@context": "https://schema.org", "@type": "FAQPage", mainEntity: faqs.map((f) => ({ "@type": "Question", name: f.q, acceptedAnswer: { "@type": "Answer", text: f.a } })) };
  return (
    <>
      <PageHero title="Frequently asked questions">Can't find your answer? Use the contact page and we'll get back to you.</PageHero>
      <Container className="max-w-4xl py-20"><Faq /></Container>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(ld).replace(/</g, "\\u003c") }} />
    </>
  );
}
