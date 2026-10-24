export default function manifest() {
  return { name: "ClinicOS", short_name: "ClinicOS", description: "Clinic management", start_url: "/", display: "standalone", background_color: "#0D0D0D", theme_color: "#0D0D0D",
    icons: [{ src: "/icon.svg", sizes: "any", type: "image/svg+xml", purpose: "any" }] };
}
