"use client";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "@/lib/auth";

export default function Index() {
  const { me, loading } = useAuth();
  const router = useRouter();
  useEffect(() => { if (!loading) router.replace(!me ? "/login" : me.role === "patient" ? "/portal" : me.role === "superadmin" ? "/admin" : "/dashboard"); }, [me, loading, router]);
  return null;
}
