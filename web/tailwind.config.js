/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/app/**/*.{ts,tsx}",
    "./src/components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: "#0b0f1a",
        panel: "#121826",
        panel2: "#1a2233",
        border: "#26304a",
        accent: "#6366f1",
        accent2: "#818cf8",
        muted: "#8b95ab",
      },
    },
  },
  plugins: [],
};
