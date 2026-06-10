import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        background: "#070b12",
        card: "#0f1623",
        "card-elevated": "#151f2e",
        border: "#2d3a4f",
        "border-bright": "#3d4f6a",
        muted: "#94a3b8",
        foreground: "#f1f5f9",
        primary: "#60a5fa",
        "primary-dim": "#3b82f6",
        success: "#4ade80",
        danger: "#f87171",
        warning: "#fbbf24",
        accent: "#22d3ee",
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(96, 165, 250, 0.25), 0 8px 32px rgba(0, 0, 0, 0.45)",
        "glow-success": "0 0 0 1px rgba(74, 222, 128, 0.3), 0 8px 28px rgba(34, 197, 94, 0.12)",
        "glow-danger": "0 0 0 1px rgba(248, 113, 113, 0.3), 0 8px 28px rgba(239, 68, 68, 0.1)",
      },
      fontFamily: {
        sans: ["var(--font-noto)", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
export default config;
