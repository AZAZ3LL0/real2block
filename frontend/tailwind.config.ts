import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        accent: { DEFAULT: "#2F7D5B", dark: "#235E44", light: "#E3F2EA" },
      },
      fontFamily: {
        pixel: ['"Press Start 2P"', "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
} satisfies Config;
