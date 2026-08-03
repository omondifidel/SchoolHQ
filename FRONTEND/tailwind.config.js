/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0B1F1B",
        panel: "#12302A",
        "panel-border": "#1E453C",
        "panel-hover": "#173A32",
        ink: "#EDEAE0",
        "ink-muted": "#8FA79E",
        "ink-faint": "#5C7268",
        gold: "#C98A34",
        "gold-hover": "#DDA04B",
        green: "#3FA184",
        red: "#E0654A",
      },
      fontFamily: {
        display: ["var(--font-space-grotesk)", "sans-serif"],
        sans: ["var(--font-inter)", "sans-serif"],
        mono: ["var(--font-plex-mono)", "monospace"],
      },
      fontFeatureSettings: {
        tabular: '"tnum" 1',
      },
      keyframes: {
        "underline-draw": {
          "0%": { transform: "scaleX(0)" },
          "100%": { transform: "scaleX(1)" },
        },
        "fade-in": {
          "0%": { opacity: "0", transform: "translateY(4px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        "underline-draw": "underline-draw 0.5s ease forwards",
        "fade-in": "fade-in 0.3s ease forwards",
      },
    },
  },
  plugins: [],
};