import "@fontsource-variable/inter";
import "@fontsource-variable/plus-jakarta-sans";
import "./globals.css";
import { headers } from "next/headers";
import Providers from "@/components/Providers";

export const metadata = { title: { default: "ClinicOS", template: "%s · ClinicOS" }, description: "ClinicOS web app", robots: { index: false } };
const themeScript = `try{var t=localStorage.getItem("theme");if(!t){t=matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light"}document.documentElement.dataset.theme=t}catch(e){}`;

export default async function RootLayout({ children }) {
  const nonce = (await headers()).get("x-nonce") || undefined;
  return (
    <html lang="en" suppressHydrationWarning>
      <head><script nonce={nonce} dangerouslySetInnerHTML={{ __html: themeScript }} /></head>
      <body suppressHydrationWarning><Providers>{children}</Providers></body>
    </html>
  );
}
