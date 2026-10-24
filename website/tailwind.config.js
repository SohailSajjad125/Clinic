module.exports = {
  content: ["./app/**/*.{js,jsx}", "./components/**/*.{js,jsx}", "./lib/**/*.js"],
  theme: {
    extend: {
      colors: {
        bg: "var(--bg)", surface: "var(--surface)", line: "var(--border)", ink: "var(--text)", mute: "var(--muted)",
        brand: "var(--accent)", primary: "var(--primary)", "primary-fg": "var(--primary-fg)", "accent-soft": "var(--accent-soft)",
        success: "rgb(var(--success-rgb) / <alpha-value>)", warning: "rgb(var(--warning-rgb) / <alpha-value>)", danger: "rgb(var(--danger-rgb) / <alpha-value>)",
        "success-ink": "var(--success-ink)", "warning-ink": "var(--warning-ink)", "danger-ink": "var(--danger-ink)", "danger-fg": "var(--danger-fg)",
      },
      fontFamily: {
        sans: ['"Inter Variable"', "system-ui", "sans-serif"],
        display: ['"Plus Jakarta Sans Variable"', '"Inter Variable"', "system-ui", "sans-serif"],
      },
      borderRadius: { card: "18px", btn: "10px" },
    },
  },
  plugins: [],
};
