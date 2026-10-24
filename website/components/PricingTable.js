"use client";
import { Check } from "lucide-react";
import { useState } from "react";
import { APP_URL, plans } from "@/lib/content";

const fmt = (n) => new Intl.NumberFormat("en-PK").format(n);

export default function PricingTable() {
  const [yearly, setYearly] = useState(true);
  return (
    <div>
      <div className="mb-10 flex items-center justify-center gap-4 text-sm font-medium">
        <span className={yearly ? "text-mute" : "text-ink"}>Monthly</span>
        <button role="switch" aria-checked={yearly} aria-label="Bill yearly" onClick={() => setYearly(!yearly)}
          className={`relative h-7 w-12 rounded-full border border-line transition-colors ${yearly ? "bg-primary" : "bg-surface"}`}>
          <span className={`absolute top-0.5 h-5 w-5 rounded-full bg-ink shadow transition-all ${yearly ? "left-6" : "left-1"}`} />
        </button>
        <span className={yearly ? "text-ink" : "text-mute"}>Yearly <span className="ml-1 rounded-full bg-accent-soft px-2 py-0.5 text-xs font-semibold text-brand">2 months free</span></span>
      </div>
      <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-4">
        {plans.map((p) => {
          const price = p.monthly === null ? null : yearly ? Math.round((p.monthly * 10) / 12) : p.monthly;
          const href = p.id === "enterprise" ? "/contact" : `${APP_URL}/signup?plan=${p.id}`;
          return (
            <div key={p.id} className={`flex flex-col rounded-card border p-7 ${p.highlight ? "border-brand bg-surface shadow-lg ring-1 ring-[var(--primary)]" : "border-line bg-surface"}`}>
              <h3 className="font-display text-xl font-bold">{p.name}</h3>
              <p className="mt-1 min-h-12 text-sm text-mute">{p.blurb}</p>
              <p className="mt-5 font-display text-4xl font-extrabold tracking-tight">
                {price === null ? "Custom" : price === 0 ? "Free" : <>PKR {fmt(price)}<span className="text-base font-medium text-mute"> /month</span></>}
              </p>
              {price > 0 && yearly && <p className="mt-1 text-xs text-mute">Billed yearly: PKR {fmt(p.monthly * 10)}</p>}
              <a href={href} className={`btn mt-6 ${p.highlight ? "btn-primary" : "btn-outline"}`}>{p.cta}</a>
              <ul className="mt-6 space-y-3 text-sm">
                {p.features.map((f) => <li key={f} className="flex gap-2.5"><Check className="mt-0.5 h-4 w-4 shrink-0 text-brand" aria-hidden="true" />{f}</li>)}
              </ul>
            </div>
          );
        })}
      </div>
    </div>
  );
}
