const api = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1").replace(/\/api\/v1\/?$/, "");
const dev = process.env.NODE_ENV === "development";
// The marketing site holds no logins or tokens. Its two inline scripts are static (theme switch, JSON-LD), so scripts use 'unsafe-inline'.
// (The web app, which does hold tokens, uses a stricter per-request nonce policy.)
const csp = [
  "default-src 'self'", `script-src 'self' 'unsafe-inline'${dev ? " 'unsafe-eval'" : ""}`, "style-src 'self' 'unsafe-inline'", "img-src 'self' data:", "font-src 'self' data:",
  `connect-src 'self' ${api}`, "object-src 'none'", "base-uri 'self'", "form-action 'self'", "frame-ancestors 'none'", ...(dev ? [] : ["upgrade-insecure-requests"]),
].join("; ");
const security = [
  { key: "Content-Security-Policy", value: csp }, { key: "X-Content-Type-Options", value: "nosniff" }, { key: "X-Frame-Options", value: "DENY" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" }, { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(), payment=(), usb=()" },
  { key: "Cross-Origin-Opener-Policy", value: "same-origin" }, { key: "Strict-Transport-Security", value: "max-age=31536000; includeSubDomains" },
];
module.exports = { reactStrictMode: true, poweredByHeader: false, productionBrowserSourceMaps: false, async headers() { return [{ source: "/:path*", headers: security }]; } };
