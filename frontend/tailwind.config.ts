import type { Config } from "tailwindcss";

/**
 * Design system de Horizon UI (github.com/horizon-ui/horizon-tailwind-react)
 * adaptado a Next.js: colores navy/brand, sombras 3xl, radio 20px y fuentes
 * Poppins + DM Sans.
 */
const config: Config = {
  darkMode: "class",
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        poppins: ["Poppins", "sans-serif"],
        dm: ["DM Sans", "sans-serif"],
      },
      boxShadow: {
        "3xl": "14px 17px 40px 4px rgba(112, 144, 176, 0.18)",
        inset: "inset 0px 18px 22px",
        darkinset: "0px 4px 4px inset",
      },
      borderRadius: {
        primary: "20px",
      },
      colors: {
        lightPrimary: "#F4F7FE",
        brandLinear: "#868CFF",
        gray: {
          50: "#f8f9fa",
          100: "#edf2f7",
          200: "#e9ecef",
          300: "#cbd5e0",
          400: "#a0aec0",
          500: "#adb5bd",
          600: "#a3aed0",
          700: "#707eae",
          800: "#252f40",
          900: "#1b2559",
        },
        navy: {
          50: "#d0dcfb",
          100: "#aac0fe",
          200: "#a3b9f8",
          300: "#728fea",
          400: "#3652ba",
          500: "#1b3bbb",
          600: "#24388a",
          700: "#1B254B",
          800: "#111c44",
          900: "#0b1437",
        },
        brand: {
          50: "#E9E3FF",
          100: "#C0B8FE",
          200: "#A195FD",
          300: "#8171FC",
          400: "#7551FF",
          500: "#422AFB",
          600: "#3311DB",
          700: "#2111A5",
          800: "#190A75",
          900: "#11085A",
        },
        green: {
          50: "#F0FDF4",
          100: "#DCFCE7",
          200: "#BBF7D0",
          300: "#86EFAC",
          400: "#4ADE80",
          500: "#22C55E",
          600: "#16B364",
          700: "#15803D",
          800: "#166534",
          900: "#14532D",
        },
      },
    },
  },
  plugins: [],
};
export default config;
