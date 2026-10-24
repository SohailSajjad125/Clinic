"use client";
import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { clearNavHistory } from "@/components/BackButton";
import { api, post, session } from "./api";

const Ctx = createContext(null);
export const useAuth = () => useContext(Ctx);

export function AuthProvider({ children }) {
  const [me, setMe] = useState(null);
  const [loading, setLoading] = useState(true);
  const qc = useQueryClient();
  const router = useRouter();

  useEffect(() => {
    if (!session.access && !session.refresh) { setLoading(false); return; }
    api("/auth/me").then(setMe).catch(() => session.clear()).finally(() => setLoading(false));
  }, []);

  const enter = useCallback((r) => { session.set(r); qc.clear(); setMe(r.me); }, [qc]);
  const login = async (email, password, audience) => { const r = await post("/auth/login", { email, password, ...(audience ? { audience } : {}) }); enter(r); return r; };
  const registerPatient = async (data) => { const r = await post("/auth/register-patient", data); enter(r); return r; };
  const register = async (data) => { const r = await post("/auth/register-clinic", data); enter(r); return r; };
  const logout = () => { clearNavHistory(); api("/auth/logout", { method: "POST" }).catch(() => {}); session.clear(); qc.clear(); setMe(null); router.replace("/login"); };

  const reload = () => api("/auth/me").then(setMe);
  return <Ctx.Provider value={{ me, loading, login, register, registerPatient, logout, reload }}>{children}</Ctx.Provider>;
}
