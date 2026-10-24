"use client";
import { motion } from "framer-motion";
import { Activity, BarChart3, Bell, Bot, Building2, CalendarClock, ClipboardList, FileText, HeartPulse, Inbox, Mail, Pill, ScrollText as LogIcon, UserRound, LayoutDashboard, LogOut, Menu, MessagesSquare, Moon, Package, Receipt, ScrollText, Search, Settings, Sun, Trash2, UserCog, Users, Volume2, VolumeX, X } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import AssistantPanel from "@/components/AssistantPanel";
import BackButton from "@/components/BackButton";
import ChangePassword from "@/components/ChangePassword";
import Logo from "@/components/Logo";
import Palette from "@/components/Palette";
import { useToast } from "@/components/Toast";
import { Skeleton } from "@/components/ui";
import { post } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Dot, ROUTE_CATEGORY, useDots, useSeen } from "@/lib/dots";
import { useApi } from "@/lib/hooks";
import { useRealtime } from "@/lib/realtime";
import { setSound, soundOn, unlockAudio } from "@/lib/sound";

const ALL = ["owner", "doctor", "receptionist", "nurse"];
// [route, label, icon, roles]  (a red dot appears on a route when something relevant to this person changes in that feature)
const STAFF_NAV = [
  ["/dashboard", "Dashboard", LayoutDashboard, ALL], ["/queue", "Live queue", Activity, ALL], ["/appointments", "Appointments", CalendarClock, ALL], ["/patients", "Patients", Users, ALL],
  ["/consultations", "Consultations", ClipboardList, ["owner", "doctor", "nurse"]], ["/billing", "Billing", Receipt, ["owner", "receptionist"]], ["/inventory", "Inventory", Package, ["owner", "receptionist", "nurse"]],
  ["/messages", "Patient messages", Inbox, ALL], ["/chat", "Team chat", MessagesSquare, ALL], ["/analytics", "Analytics", BarChart3, ["owner"]], ["/staff", "Team & doctors", UserCog, ["owner", "receptionist", "nurse"]],
  ["/settings", "Settings", Settings, ["owner", "doctor", "receptionist"]], ["/audit", "Audit log", ScrollText, ["owner"]], ["/trash", "Deleted history", Trash2, ["owner"]],
];
const BOTTOM = [["/dashboard", "Home", LayoutDashboard], ["/patients", "Patients", Users], ["/appointments", "Visits", CalendarClock], ["/chat", "Chat", MessagesSquare]];
// Patients and platform admins get their options in the left sidebar too: [address, label, icon, red-dot category, tab key]
const PATIENT_NAV = [["/portal", "Overview", HeartPulse, null, "overview"], ["/portal?tab=appointments", "Appointments", CalendarClock, "appointments", "appointments"], ["/portal?tab=prescriptions", "Prescriptions", Pill, "prescriptions", "prescriptions"],
  ["/portal?tab=documents", "Documents", FileText, "documents", "documents"], ["/portal?tab=invoices", "Invoices", Receipt, "invoices", "invoices"], ["/portal?tab=messages", "Messages", MessagesSquare, "messages", "messages"], ["/notifications", "Notifications", Bell]];
const ADMIN_NAV = [["/admin", "Overview", LayoutDashboard, null, "overview"], ["/admin?tab=clinics", "Clinics", Building2, "admin_clinics", "clinics"], ["/admin?tab=users", "Users", UserRound, null, "users"], ["/admin?tab=audit", "Audit log", LogIcon, null, "audit"],
  ["/admin?tab=support", "Support", Mail, "admin_support", "support"], ["/admin?tab=messaging", "Messaging log", Inbox, null, "messaging"], ["/admin?tab=health", "System health", Activity, null, "health"], ["/admin?tab=settings", "Settings", Settings, null, "settings"], ["/notifications", "Notifications", Bell]];
const category = (path) => Object.entries(ROUTE_CATEGORY).find(([r]) => path === r || path.startsWith(r + "/"))?.[1];

function Shell({ children }) {
  const { me, loading, logout, reload } = useAuth();
  const sp = useSearchParams();
  const curTab = sp.get("tab") || "overview";
  const router = useRouter();
  const path = usePathname();
  const toast = useToast();
  const seen = useSeen();
  const [menu, setMenu] = useState(false);
  const [ai, setAi] = useState(false);
  const [pal, setPal] = useState(false);
  const [theme, setTheme] = useState("light");
  const [sound, setSoundState] = useState(true);
  const role = me?.role;
  const staff = ALL.includes(role);
  const locked = !!me?.must_change_password;
  useRealtime(!!me && !locked);
  const { dots, total } = useDots(!!me && !locked);
  const notes = useApi("notifications", "/notifications", { enabled: !!me && !locked });

  useEffect(() => { if (!loading && !me) router.replace("/login"); }, [loading, me, router]);
  useEffect(() => {
    if (!role) return;
    if (role === "patient" && !(path.startsWith("/portal") || path.startsWith("/notifications"))) router.replace("/portal");
    if (role === "superadmin" && !(path.startsWith("/admin") || path.startsWith("/notifications"))) router.replace("/admin");
    if (staff && (path.startsWith("/portal") || path.startsWith("/admin"))) router.replace("/dashboard");
  }, [role, path, staff, router]);
  useEffect(() => setMenu(false), [path]);
  useEffect(() => { setTheme(document.documentElement.dataset.theme || "light"); setSoundState(soundOn()); unlockAudio(); }, []);
  useEffect(() => { const c = category(path); if (c && dots[c]) seen(c); }, [path, dots]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { document.title = (total ? `(${total}) ` : "") + "ClinicOS"; }, [total]);
  useEffect(() => {
    const k = (e) => {
      if (!(e.ctrlKey || e.metaKey)) return;
      const key = e.key.toLowerCase();
      if (key === "k") { e.preventDefault(); setPal((v) => !v); }
      if (key === "j" && staff) { e.preventDefault(); setAi((v) => !v); }
    };
    document.addEventListener("keydown", k); return () => document.removeEventListener("keydown", k);
  }, [staff]);
  const flip = () => { const n = theme === "dark" ? "light" : "dark"; document.documentElement.dataset.theme = n; try { localStorage.setItem("theme", n); } catch {} setTheme(n); };
  const toggleSound = () => { setSound(!sound); setSoundState(!sound); };

  if (loading || !me) return <div className="mx-auto max-w-3xl p-10"><Skeleton rows={5} /></div>;
  if (locked) return <ChangePassword onDone={reload} onLogout={logout} />;
  const items = staff ? STAFF_NAV.filter(([, , , roles]) => roles.includes(role))
    : role === "patient" ? PATIENT_NAV : ADMIN_NAV;
  const unread = notes.data?.unread || 0;
  const hiddenDots = items.some(([h]) => !BOTTOM.some(([b]) => b === h) && dots[category(h)]);

  const Sidebar = (
    <nav className="flex h-full flex-col" aria-label="Main">
      <div className="px-5 py-5"><Logo /></div>
      <ul className="flex-1 space-y-1 overflow-y-auto px-3">
        {items.map(([href, label, Icon, cat, tabKey]) => {
          const base = href.split("?")[0];
          const on = tabKey !== undefined ? path === base && curTab === tabKey : path === href || path.startsWith(href + "/");
          const c = cat !== undefined ? cat : category(href);
          return (
            <li key={href}><Link href={href} aria-current={on ? "page" : undefined} className={`relative flex items-center gap-3 rounded-btn px-3 py-2.5 text-sm font-medium transition-colors ${on ? "text-brand" : "text-mute hover:text-ink"}`}>
              {on && <motion.span layoutId="nav-pill" className="absolute inset-0 rounded-btn" style={{ background: "color-mix(in srgb, var(--primary) 12%, transparent)" }} transition={{ type: "spring", stiffness: 400, damping: 34 }} />}
              <span className="relative"><Icon className="h-[18px] w-[18px]" aria-hidden="true" /><Dot show={!!(c && dots[c])} /></span><span className="relative">{label}</span>
              {c && dots[c] ? <span className="relative ml-auto grid h-5 min-w-5 place-items-center rounded-full bg-danger px-1 text-[10px] font-bold text-danger-fg" aria-label={`${dots[c]} new`}>{dots[c] > 9 ? "9+" : dots[c]}</span> : null}</Link></li>);
        })}
      </ul>
      <div className="border-t border-line p-4">
        <p className="truncate text-sm font-semibold">{me.full_name}</p>
        <p className="truncate text-xs capitalize text-mute">{role === "superadmin" ? "Platform admin" : role}{me.clinic ? ` · ${me.clinic.name}` : ""}</p>
        <button onClick={logout} className="mt-3 flex items-center gap-2 text-sm text-mute hover:text-ink"><LogOut className="h-4 w-4" />Log out</button>
      </div>
    </nav>
  );

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[250px_1fr]">
      <aside className="sticky top-0 hidden h-screen border-r border-line bg-surface lg:block">{Sidebar}</aside>
      {menu && <div className="fixed inset-0 z-[60] lg:hidden"><div className="absolute inset-0 bg-black/40" onClick={() => setMenu(false)} /><div className="absolute left-0 top-0 h-full w-72 bg-surface shadow-2xl">{Sidebar}</div></div>}
      <div className="min-w-0 pb-20 lg:pb-0">
        {!me.email_verified && staff && (
          <div role="status" className="flex flex-wrap items-center justify-center gap-3 bg-warning/15 px-4 py-2 text-sm">Please verify your email address.
            <button className="font-semibold underline" onClick={() => post("/auth/resend-verification").then(() => toast("Verification email sent", "success")).catch((e) => toast(e.message, "error"))}>Resend email</button></div>)}
        <header className="glass sticky top-0 z-40 flex h-16 items-center justify-between gap-2 border-b border-line px-4 sm:px-8">
          <div className="flex items-center gap-2">
            <button className="rounded-lg p-2 lg:hidden" onClick={() => setMenu(!menu)} aria-label="Open menu">{menu ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}</button>
            <BackButton />
            {staff && <button onClick={() => setPal(true)} className="hidden items-center gap-2 rounded-btn border border-line bg-surface px-3 py-2 text-sm text-mute hover:border-brand xl:flex"><Search className="h-4 w-4" />Search or jump to…<kbd className="ml-6 rounded border border-line px-1.5 text-[10px]">Ctrl K</kbd></button>}
          </div>
          <div className="flex items-center gap-2">
            {staff && <button onClick={() => setPal(true)} aria-label="Search" className="grid h-10 w-10 place-items-center rounded-btn border border-line bg-surface xl:hidden"><Search className="h-4 w-4" /></button>}
            {staff && <button onClick={() => setAi(true)} className="btn btn-outline btn-sm"><Bot className="h-4 w-4" />Assistant<kbd className="ml-1 hidden rounded border border-line px-1.5 text-[10px] text-mute sm:inline">Ctrl J</kbd></button>}
            <button onClick={toggleSound} aria-label={sound ? "Mute notification sound" : "Turn on notification sound"} aria-pressed={!sound} className="grid h-10 w-10 place-items-center rounded-btn border border-line bg-surface hover:border-brand">{sound ? <Volume2 className="h-4 w-4" /> : <VolumeX className="h-4 w-4 text-mute" />}</button>
            <Link href="/notifications" aria-label={`Notifications, ${unread} unread`} className="relative grid h-10 w-10 place-items-center rounded-btn border border-line bg-surface hover:border-brand">
              <Bell className="h-4 w-4" />{unread > 0 && <span className="absolute -right-1 -top-1 grid h-5 min-w-5 place-items-center rounded-full bg-danger px-1 text-[10px] font-bold text-danger-fg">{unread > 9 ? "9+" : unread}</span>}</Link>
            <button onClick={flip} aria-label="Toggle theme" className="grid h-10 w-10 place-items-center rounded-btn border border-line bg-surface hover:border-brand">{theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}</button>
          </div>
        </header>
        <main className="mx-auto max-w-6xl px-4 py-8 sm:px-8">{children}</main>
      </div>
      {staff && (
        <nav aria-label="Quick navigation" className="glass fixed inset-x-0 bottom-0 z-40 grid grid-cols-5 border-t border-line pb-[env(safe-area-inset-bottom)] lg:hidden">
          {BOTTOM.map(([href, label, Icon]) => <Link key={href} href={href} className={`flex flex-col items-center gap-1 py-2.5 text-[11px] font-medium ${path.startsWith(href) ? "text-brand" : "text-mute"}`}><span className="relative"><Icon className="h-5 w-5" aria-hidden="true" /><Dot show={!!dots[category(href)]} /></span>{label}</Link>)}
          <button onClick={() => setMenu(true)} className="flex flex-col items-center gap-1 py-2.5 text-[11px] font-medium text-mute"><span className="relative"><Menu className="h-5 w-5" aria-hidden="true" /><Dot show={hiddenDots} /></span>More</button>
        </nav>)}
      {staff && <AssistantPanel open={ai} onClose={() => setAi(false)} />}
      <Palette open={pal} onClose={() => setPal(false)} role={role} />
    </div>
  );
}

export default function AppLayout({ children }) {
  return <Suspense fallback={<div className="mx-auto max-w-3xl p-10"><Skeleton rows={5} /></div>}><Shell>{children}</Shell></Suspense>;
}
