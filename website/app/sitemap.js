import { articles, SITE_URL } from "@/lib/content";

export default function sitemap() {
  const pages = ["", "/features", "/solutions", "/pricing", "/security", "/resources", "/about", "/contact", "/faq", "/privacy", "/terms"];
  return [
    ...pages.map((p) => ({ url: `${SITE_URL}${p}`, changeFrequency: "monthly", priority: p === "" ? 1 : 0.7 })),
    ...articles.map((a) => ({ url: `${SITE_URL}/resources/${a.slug}`, lastModified: a.date, priority: 0.6 })),
  ];
}
