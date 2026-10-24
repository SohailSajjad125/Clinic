"use client";
import { ArrowLeft } from "lucide-react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

const KEY = "cos_nav";
const ROOTS = ["/dashboard", "/portal", "/admin", "/onboarding"];
const read = () => { try { return JSON.parse(sessionStorage.getItem(KEY) || "[]"); } catch { return []; } };
const write = (v) => { try { sessionStorage.setItem(KEY, JSON.stringify(v.slice(-40))); } catch {} };
export const clearNavHistory = () => { try { sessionStorage.removeItem(KEY); } catch {} };

/**
 * Walks back through the screens you actually visited, one step at a time (including tabs, which live in the address bar).
 * It keeps its own short trail so it also works for pages opened directly, where it goes up one level instead.
 */
function Inner() {
  const router = useRouter();
  const path = usePathname();
  const sp = useSearchParams();
  const here = path + (sp.toString() ? `?${sp.toString()}` : "");
  const [trail, setTrail] = useState([]);
  useEffect(() => {
    const st = read();
    if (st[st.length - 1] !== here) { if (st.length > 1 && st[st.length - 2] === here) st.pop(); else st.push(here); write(st); }
    setTrail(read());
  }, [here]);
  const atRoot = ROOTS.includes(path) && !sp.get("tab");
  if (atRoot && trail.length < 2) return null;
  if (atRoot && !sp.get("tab")) return null;
  const back = () => {
    const st = read();
    if (st.length > 1) { st.pop(); write(st); return router.push(st[st.length - 1]); }
    if (sp.get("tab")) return router.push(path);
    router.push(path.split("/").slice(0, -1).join("/") || "/dashboard");
  };
  return (
    <button onClick={back} aria-label="Go back" className="inline-flex h-10 items-center gap-1.5 rounded-btn border border-line bg-surface px-3 text-sm font-medium hover:border-brand">
      <ArrowLeft className="h-4 w-4" aria-hidden="true" /><span className="hidden sm:inline">Back</span>
    </button>
  );
}
export default function BackButton() { return <Suspense fallback={null}><Inner /></Suspense>; }
