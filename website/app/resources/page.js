import Link from "next/link";
import { Container, PageHero } from "@/components/ui";
import { articles } from "@/lib/content";

export const metadata = { title: "Resources", description: "Practical guides for running a clinic: reducing no-shows, going digital, and using AI safely." };
const date = (d) => new Date(d).toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" });

export default function Resources() {
  return (
    <>
      <PageHero title="Practical reading for clinic owners">Short guides on the operational problems clinics tell us about most.</PageHero>
      <Container className="grid gap-5 py-20 md:grid-cols-3">
        {articles.map((a) => (
          <Link key={a.slug} href={`/resources/${a.slug}`} className="group flex flex-col rounded-card border border-line bg-surface p-7 transition-transform duration-300 hover:-translate-y-1">
            <p className="text-xs text-mute">{date(a.date)} · {a.minutes} min read</p>
            <h2 className="mt-3 font-display text-xl font-bold group-hover:text-brand">{a.title}</h2>
            <p className="mt-3 leading-7 text-mute">{a.summary}</p>
          </Link>
        ))}
      </Container>
    </>
  );
}
