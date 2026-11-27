import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        sand: { 50: "#fbf8f2", 100: "#f3ede1", 200: "#e6dfcf" },
        brand: { 50: "#e6f6ee", 500: "#059669", 600: "#047857", 700: "#065f46", 900: "#0b3b2e" },
      },
      boxShadow: {
        soft: "0 10px 30px rgba(20, 40, 31, 0.07)",
        lift: "0 18px 44px rgba(20, 40, 31, 0.12)",
      },
      keyframes: {
        rise: { from: { opacity: "0", transform: "translateY(10px)" }, to: { opacity: "1", transform: "none" } },
      },
      animation: { rise: "rise .45s ease-out both" },
    },
  },
  plugins: [],
};

export default config;
