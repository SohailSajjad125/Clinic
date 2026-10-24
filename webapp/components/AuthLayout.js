"use client";
import { motion } from "framer-motion";
import { useRouter } from "next/navigation";
import { useEffect, useRef } from "react";
import { useAuth } from "@/lib/auth";
import { SITE } from "@/lib/api";
import Logo from "./Logo";

function Art({ patient }) {
  return (
    <div className="hero-glow relative hidden overflow-hidden p-12 lg:flex lg:flex-col lg:justify-between">
      <a href={SITE}><Logo light /></a>
      <div className="relative">
        <svg viewBox="0 0 600 200" className="mb-10 w-full max-w-lg" aria-hidden="true">
          <motion.path d="M0 110h130l28-70 48 130 36-60h70l24-34 30 34h234" fill="none" stroke="var(--primary)" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round"
            initial={{ pathLength: 0, opacity: 0 }} animate={{ pathLength: 1, opacity: 1 }} transition={{ duration: 2.2, ease: "easeInOut" }} />
          <motion.path d="M0 110h130l28-70 48 130 36-60h70l24-34 30 34h234" fill="none" stroke="var(--primary)" strokeWidth="14" strokeLinecap="round" opacity="0.12"
            initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 2.2, ease: "easeInOut" }} />
        </svg>
        <h2 className="max-w-md font-display text-4xl font-extrabold leading-tight tracking-tight">{patient ? "Your care, in one place." : "Run your clinic. Care for your patients."}</h2>
        <p className="mt-4 max-w-md text-mute">{patient ? "Book visits, see your prescriptions and reports, and message your clinic." : "Appointments, records, prescriptions and billing in one calm workspace."}</p>
      </div>
      <p className="text-xs text-mute">© 2026 ClinicOS</p>
    </div>
  );
}

export default function AuthLayout({ children, patient = false }) {
  const { me, loading } = useAuth();
  const router = useRouter();
  const wasSignedIn = useRef(null); // only bounce people who arrive already signed in, not ones who just signed in on this page
  if (!loading && wasSignedIn.current === null) wasSignedIn.current = !!me;
  useEffect(() => { if (!loading && me && wasSignedIn.current) router.replace(me.role === "patient" ? "/portal" : me.role === "superadmin" ? "/admin" : "/dashboard"); }, [me, loading, router]);
  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <Art patient={patient} />
      <main className="flex items-center justify-center p-6 sm:p-12">
        <motion.div initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }} className="w-full max-w-md">
          <div className="mb-8 lg:hidden"><Logo /></div>
          {children}
        </motion.div>
      </main>
    </div>
  );
}
