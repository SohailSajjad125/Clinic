"use client";
import { AnimatePresence, motion } from "framer-motion";
import { X } from "lucide-react";
import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";

export function Modal({ open, onClose, title, children, wide = false }) {
  const ref = useRef(null);
  const pressedOnBackdrop = useRef(false);
  useEffect(() => {
    if (!open) return;
    const k = (e) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", k);
    const t = setTimeout(() => ref.current?.querySelector("input,select,textarea,button")?.focus(), 60);
    return () => { document.removeEventListener("keydown", k); clearTimeout(t); };
  }, [open, onClose]);
  return (
    <AnimatePresence>
      {open && (
        <motion.div className="fixed inset-0 z-[90] grid place-items-center overflow-hidden bg-black/50 p-4 backdrop-blur-sm" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
          onPointerDown={(e) => { pressedOnBackdrop.current = e.target === e.currentTarget; }} onClick={(e) => { if (pressedOnBackdrop.current && e.target === e.currentTarget) onClose(); pressedOnBackdrop.current = false; }}>
          <motion.div ref={ref} role="dialog" aria-modal="true" aria-label={title} initial={{ opacity: 0, y: 24, scale: 0.97 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: 12 }}
            transition={{ type: "spring", stiffness: 380, damping: 30 }} className={`card max-h-[calc(100dvh-2rem)] w-full overflow-y-auto overscroll-contain ${wide ? "max-w-2xl" : "max-w-md"} p-6 shadow-2xl`}>
            <div className="sticky -top-6 z-10 -mx-6 -mt-6 mb-5 flex items-center justify-between bg-surface px-6 pb-3 pt-6"><h2 className="font-display text-xl font-bold">{title}</h2>
              <button onClick={onClose} aria-label="Close" className="rounded-lg p-1.5 text-mute hover:bg-bg"><X className="h-5 w-5" /></button></div>
            {children}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

const C = createContext(async () => false);
export const useConfirm = () => useContext(C);

export function ConfirmProvider({ children }) {
  const [s, setS] = useState(null);
  const confirm = useCallback((opts) => new Promise((resolve) => setS({ ...opts, resolve })), []);
  const close = (v) => { s.resolve(v); setS(null); };
  return (
    <C.Provider value={confirm}>
      {children}
      <Modal open={!!s} onClose={() => close(false)} title={s?.title || "Are you sure?"}>
        <p className="leading-7 text-mute">{s?.body}</p>
        <div className="mt-6 flex justify-end gap-3">
          <button className="btn btn-outline" onClick={() => close(false)}>Cancel</button>
          <button className={`btn ${s?.danger ? "btn-danger" : "btn-primary"}`} onClick={() => close(true)}>{s?.action || "Confirm"}</button>
        </div>
      </Modal>
    </C.Provider>
  );
}
