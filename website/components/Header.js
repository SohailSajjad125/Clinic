"use client";
import { AnimatePresence, motion } from "framer-motion";
import { Menu, X } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { APP_URL, nav } from "@/lib/content";
import Logo from "./Logo";
import ThemeToggle from "./ThemeToggle";

export default function Header() {
  const path = usePathname();
  const [open, setOpen] = useState(false);
  useEffect(() => setOpen(false), [path]);
  return (
    <header className="glass sticky top-0 z-50 border-b border-line">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-5 sm:px-8">
        <Link href="/" aria-label="ClinicOS home"><Logo /></Link>
        <nav className="hidden items-center gap-1 lg:flex" aria-label="Main">
          {nav.map((n) => (
            <Link key={n.href} href={n.href} aria-current={path.startsWith(n.href) ? "page" : undefined}
              className={`rounded-btn px-3 py-2 text-sm font-medium transition-colors hover:text-brand ${path.startsWith(n.href) ? "text-brand" : "text-mute"}`}>
              {n.label}
            </Link>
          ))}
        </nav>
        <div className="flex items-center gap-2">
          <ThemeToggle />
          <details className="group relative hidden sm:block"><summary className="btn btn-outline cursor-pointer list-none [&::-webkit-details-marker]:hidden">For patients</summary><div className="absolute right-0 mt-2 w-52 rounded-xl border border-line bg-surface p-2 shadow-xl"><a href={`${APP_URL}/patient/login`} className="block rounded-lg px-3 py-2 text-sm hover:bg-bg">Patient log in</a><a href={`${APP_URL}/patient/signup`} className="block rounded-lg px-3 py-2 text-sm hover:bg-bg">Create patient account</a></div></details>
          <a href={`${APP_URL}/login`} className="btn btn-outline hidden sm:inline-flex">Clinic log in</a>
          <a href={`${APP_URL}/signup`} className="btn btn-primary hidden sm:inline-flex">Clinic sign up</a>
          <button className="grid h-10 w-10 place-items-center rounded-btn border border-line bg-surface lg:hidden" onClick={() => setOpen(!open)}
            aria-expanded={open} aria-label={open ? "Close menu" : "Open menu"}>
            {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
      </div>
      <AnimatePresence>
        {open && (
          <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25 }} className="overflow-hidden border-t border-line bg-bg lg:hidden">
            <nav className="flex flex-col gap-1 px-5 py-4" aria-label="Mobile">
              {nav.map((n) => <Link key={n.href} href={n.href} className="rounded-btn px-3 py-3 font-medium text-ink hover:bg-surface">{n.label}</Link>)}
              <Link href="/contact" className="rounded-btn px-3 py-3 font-medium text-ink hover:bg-surface">Contact</Link>
              <p className="mt-3 px-3 text-xs font-semibold text-mute">For clinics</p><div className="grid grid-cols-2 gap-3"><a href={`${APP_URL}/login`} className="btn btn-outline">Log in</a><a href={`${APP_URL}/signup`} className="btn btn-primary">Sign up</a></div>
              <p className="mt-3 px-3 text-xs font-semibold text-mute">For patients</p><div className="grid grid-cols-2 gap-3"><a href={`${APP_URL}/patient/login`} className="btn btn-outline">Log in</a><a href={`${APP_URL}/patient/signup`} className="btn btn-primary">Sign up</a></div>
            </nav>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  );
}
