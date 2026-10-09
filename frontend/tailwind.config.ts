import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        marca: { 50: "#f0f5fa", 600: "#2c5282", 700: "#1a365d", 800: "#14284a" },
      },
    },
  },
  plugins: [],
};
export default config;
