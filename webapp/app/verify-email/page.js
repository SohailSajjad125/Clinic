"use client";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import AuthLayout from "@/components/AuthLayout";
import { post } from "@/lib/api";

function Inner() {
  const token = useSearchParams().get("token");
  const [s, setS] = useState({ status: "loading", msg: "" });
  useEffect(() => {
    if (!token) return setS({ status: "error", msg: "This link is incomplete." });
    post("/auth/verify-email", { token }).then(() => setS({ status: "ok" })).catch((e) => setS({ status: "error", msg: e.message }));
  }, [token]);
  return (
    <AuthLayout>
      <h1 className="font-display text-3xl font-extrabold tracking-tight">{s.status === "ok" ? "Email verified" : s.status === "error" ? "Couldn't verify" : "Verifying…"}</h1>
      {s.status === "error" && <p role="alert" className="mt-4 text-danger-ink">{s.msg}</p>}
      <p className="mt-6"><Link href="/dashboard" className="btn btn-primary">Continue to ClinicOS</Link></p>
    </AuthLayout>
  );
}
export default function Verify() { return <Suspense><Inner /></Suspense>; }
