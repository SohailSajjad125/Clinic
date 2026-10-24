import { ChevronDown } from "lucide-react";
import { faqs } from "@/lib/content";

export default function Faq({ limit }) {
  return (
    <div className="divide-y divide-line rounded-card border border-line bg-surface">
      {faqs.slice(0, limit).map((f) => (
        <details key={f.q} className="group px-6 py-5">
          <summary className="flex cursor-pointer list-none items-center justify-between gap-4 font-semibold [&::-webkit-details-marker]:hidden">
            {f.q}<ChevronDown className="h-5 w-5 shrink-0 text-mute transition-transform duration-200 group-open:rotate-180" aria-hidden="true" />
          </summary>
          <p className="mt-3 max-w-3xl leading-7 text-mute">{f.a}</p>
        </details>
      ))}
    </div>
  );
}
