import "@fontsource-variable/inter";
import "@fontsource-variable/plus-jakarta-sans";
import "./globals.css";
import Footer from "@/components/Footer";
import Header from "@/components/Header";
import { SITE_URL } from "@/lib/content";

export const metadata = {
  metadataBase: new URL(SITE_URL),
  title: { default: "ClinicOS: the operating system for modern clinics", template: "%s · ClinicOS" },
  description: "Manage patients, appointments, records, prescriptions and billing from one secure platform, with an AI assistant that helps with the admin.",
  openGraph: { title: "ClinicOS", description: "The operating system for modern clinics.", type: "website", siteName: "ClinicOS" },
  twitter: { card: "summary_large_image" },
  alternates: { canonical: "/" },
};

const themeScript = `try{var t=localStorage.getItem("theme");if(!t){t=matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light"}document.documentElement.dataset.theme=t}catch(e){}`;

export default function RootLayout({ children }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head><script dangerouslySetInnerHTML={{ __html: themeScript }} /></head>
      <body suppressHydrationWarning>
        <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[60] focus:rounded-btn focus:bg-surface focus:px-4 focus:py-2">Skip to content</a>
        <Header />
        <main id="main">{children}</main>
        <Footer />
      </body>
    </html>
  );
}
