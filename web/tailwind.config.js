/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/app/**/*.{ts,tsx}",
    "./src/components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Light-first surfaces
        canvas: "#f6f7fb",      // page background
        surface: "#ffffff",     // cards / panels
        subtle: "#f8fafc",      // very light fill
        border: "#e6e8f0",
        ring: "#c7d2fe",
        // Text
        ink: "#0f172a",         // headings
        body: "#475569",        // body text
        muted: "#94a3b8",       // secondary
        // Accent (indigo/violet)
        brand: "#6366f1",
        "brand-600": "#4f46e5",
        "brand-50": "#eef2ff",
        // Semantic
        success: "#16a34a",
        "success-50": "#f0fdf4",
        warning: "#d97706",
        "warning-50": "#fffbeb",
        danger: "#dc2626",
        "danger-50": "#fef2f2",
      },
      borderRadius: {
        xl: "0.875rem",
        "2xl": "1.125rem",
        "3xl": "1.5rem",
      },
      boxShadow: {
        card: "0 1px 2px rgba(16,24,40,0.04), 0 1px 3px rgba(16,24,40,0.06)",
        "card-hover": "0 8px 24px rgba(16,24,40,0.10)",
        soft: "0 2px 8px rgba(16,24,40,0.06)",
      },
      backgroundImage: {
        "brand-gradient": "linear-gradient(135deg,#6366f1 0%,#8b5cf6 100%)",
        "hero-gradient":
          "radial-gradient(1200px 600px at 80% -10%, #eef2ff 0%, transparent 60%), radial-gradient(1000px 500px at 0% 10%, #f5f3ff 0%, transparent 55%)",
      },
      keyframes: {
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(12px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        shimmer: {
          "100%": { transform: "translateX(100%)" },
        },
        float: {
          "0%,100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-8px)" },
        },
      },
      animation: {
        "fade-up": "fade-up 0.5s ease-out both",
        shimmer: "shimmer 1.5s infinite",
        float: "float 4s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
