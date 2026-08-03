/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        paper: "#FAF6F0",
        ink: "#0A0A0A",
        vermillion: "#FF3B30",
        blueprint: "#0A84FF",
        success: "#00A676",
        zinc: {
          50: "#FAFAFA",
          100: "#F5F5F5",
          200: "#E5E5E5",
          300: "#D4D4D4",
          400: "#A3A3A3",
          500: "#737373",
          600: "#52525B",
          700: "#3F3F46",
          800: "#27272A",
          900: "#18181B",
          950: "#09090B",
        }
      },
      fontFamily: {
        display: ["Instrument Serif", "Newsreader", "serif"],
        sans: ["Geist", "Geist Sans", "system-ui", "sans-serif"],
        mono: ["Geist Mono", "JetBrains Mono", "monospace"],
      },
      borderRadius: {
        none: "0px",
        sm: "4px",
        md: "10px",
        lg: "14px",
        xl: "18px",
      },
      boxShadow: {
        brutal: "4px 4px 0px 0px #0A0A0A",
        "brutal-sm": "2px 2px 0px 0px #0A0A0A",
        "brutal-lg": "6px 6px 0px 0px #0A0A0A",
      },
      animation: {
        "pulse-slow": "pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite",
      }
    },
  },
  plugins: [],
};
