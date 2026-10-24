"use client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import { AuthProvider } from "@/lib/auth";
import { ConfirmProvider } from "./Modal";
import { ToastProvider } from "./Toast";

export default function Providers({ children }) {
  const [qc] = useState(() => new QueryClient({ defaultOptions: { queries: { staleTime: 15_000, retry: (n, e) => e?.status !== 401 && e?.status !== 403 && e?.status !== 404 && n < 2, refetchOnWindowFocus: true } } }));
  return <QueryClientProvider client={qc}><ToastProvider><ConfirmProvider><AuthProvider>{children}</AuthProvider></ConfirmProvider></ToastProvider></QueryClientProvider>;
}
