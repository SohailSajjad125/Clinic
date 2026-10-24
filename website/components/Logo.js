export default function Logo({ dark = false }) {
  return (
    <span className="inline-flex items-center gap-2.5 font-display text-lg font-extrabold tracking-tight">
      <svg width="30" height="30" viewBox="0 0 64 64" aria-hidden="true">
        <rect width="64" height="64" rx="16" fill="#1C1B18" />
        <path d="M10 34h13l5-13 8 24 6-11h12" fill="none" stroke="var(--accent)" strokeWidth="5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      <span className={"text-ink"}>ClinicOS</span>
    </span>
  );
}
