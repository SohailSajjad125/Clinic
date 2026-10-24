"use client";
import { AnimatePresence, motion } from "framer-motion";
import { AlertCircle, Bell, CheckCircle2 } from "lucide-react";
import { createContext, useCallback, useContext, useState } from "react";

const Ctx = createContext(() => {});
export const useToast = () => useContext(Ctx);
const icon = { success: CheckCircle2, error: AlertCircle, info: Bell };
const tone = { success: "text-success-ink", error: "text-danger-ink", info: "text-brand" };

export function ToastProvider({ children }) {
  const [items, setItems] = useState([]);
  const toast = useCallback((message, kind = "info", onClick) => {
    const id = Math.random().toString(36).slice(2);
    setItems((l) => [...l.slice(-3), { id, message, kind, onClick }]);
    setTimeout(() => setItems((l) => l.filter((x) => x.id !== id)), kind === "error" ? 6000 : 4000);
  }, []);
  return (
    <Ctx.Provider value={toast}>
      {children}
      <div className="pointer-events-none fixed bottom-4 right-4 z-[100] flex w-[min(92vw,380px)] flex-col gap-2" role="status" aria-live="polite">
        <AnimatePresence>
          {items.map((t) => {
            const I = icon[t.kind];
            return (
              <motion.div key={t.id} layout initial={{ opacity: 0, y: 16, scale: 0.97 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, x: 40 }}
                onClick={t.onClick} role={t.onClick ? "link" : undefined} className={`pointer-events-auto flex items-start gap-3 rounded-xl border border-line bg-surface px-4 py-3 text-sm shadow-xl ${t.onClick ? "cursor-pointer hover:border-brand" : ""}`}>
                <I className={`mt-0.5 h-4 w-4 shrink-0 ${tone[t.kind]}`} aria-hidden="true" /><span>{t.message}</span>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>
    </Ctx.Provider>
  );
}
