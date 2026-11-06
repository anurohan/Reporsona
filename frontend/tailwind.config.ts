import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx,js,jsx,mdx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        void: {
          950: "#05060f",
          900: "#0a0b1a",
          800: "#111227",
          700: "#1a1c38",
        },
        indigoGlow: {
          400: "#8b93ff",
          500: "#6b6bff",
          600: "#5a4bff",
        },
        accent: {
          cyan: "#5ee7f2",
          violet: "#a78bfa",
          rose: "#fb7bb0",
          amber: "#f5c15a",
        },
      },
      fontFamily: {
        display: ['"Space Grotesk"', "system-ui", "sans-serif"],
        sans: ['"Inter"', "system-ui", "sans-serif"],
      },
      boxShadow: {
        glow: "0 0 40px -8px rgba(122,114,255,0.55)",
        "glow-lg": "0 0 80px -10px rgba(122,114,255,0.6)",
      },
      backgroundImage: {
        "space-gradient":
          "radial-gradient(ellipse at 20% -10%, rgba(90,75,255,0.25), transparent 55%), radial-gradient(ellipse at 90% 10%, rgba(94,231,242,0.14), transparent 50%), linear-gradient(180deg, #05060f 0%, #0a0b1a 100%)",
      },
      keyframes: {
        floaty: {
          "0%,100%": { transform: "translateY(0px)" },
          "50%": { transform: "translateY(-10px)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
        pulseGlow: {
          "0%,100%": { opacity: "0.6" },
          "50%": { opacity: "1" },
        },
      },
      animation: {
        floaty: "floaty 6s ease-in-out infinite",
        shimmer: "shimmer 2.2s linear infinite",
        pulseGlow: "pulseGlow 2.4s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

export default config;
