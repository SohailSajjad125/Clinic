import Link from "next/link";
import { Container } from "@/components/ui";

export const metadata = { title: "Page not found" };
export default function NotFound() {
  return (
    <Container className="py-32 text-center">
      <p className="font-display text-6xl font-extrabold text-brand">404</p>
      <h1 className="mt-4 font-display text-3xl font-bold">We couldn't find that page</h1>
      <p className="mt-3 text-mute">It may have moved, or the link may be mistyped.</p>
      <Link href="/" className="btn btn-primary mt-8">Back to home</Link>
    </Container>
  );
}
