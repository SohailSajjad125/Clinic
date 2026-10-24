import { SITE_URL } from "@/lib/content";

export default function robots() {
  return { rules: { userAgent: "*", allow: "/" }, sitemap: `${SITE_URL}/sitemap.xml` };
}
