import Link from "next/link";
import { notFound } from "next/navigation";
import { Container, CtaBand } from "@/components/ui";
import { articles } from "@/lib/content";

export const dynamicParams = false;
export const generateStaticParams = () => articles.map((a) => ({ slug: a.slug }));

export async function generateMetadata({ params }) {
  const { slug } = await params;
  const a = articles.find((x) => x.slug === slug);
  return a ? { title: a.title, description: a.summary, alternates: { canonical: `/resources/${a.slug}` } } : {};
}

export default async function Article({ params }) {
  const { slug } = await params;
  const a = articles.find((x) => x.slug === slug);
  if (!a) notFound();
  return (
    <>
      <Container className="max-w-3xl py-16">
        <Link href="/resources" className="text-sm font-semibold text-brand">← All resources</Link>
        <h1 className="mt-6 font-display text-4xl font-extrabold leading-tight tracking-tight md:text-5xl">{a.title}</h1>
        <p className="mt-4 text-sm text-mute">{new Date(a.date).toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" })} · {a.minutes} min read</p>
        <article className="prose-c mt-10 text-lg">
          {a.body.map((b, i) => (typeof b === "string" ? <p key={i}>{b}</p> : <h2 key={i}>{b.h}</h2>))}
        </article>
      </Container>
      <CtaBand />
    </>
  );
}
