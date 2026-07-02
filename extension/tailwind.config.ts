import type { Config } from "tailwindcss";

export default {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      boxShadow: {
        "edson-panel": "0 18px 48px rgba(15, 23, 42, 0.22)"
      }
    }
  },
  plugins: []
} satisfies Config;
