/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        sj: {
          50: "#f3f7fb",
          100: "#e3edf6",
          500: "#2563eb",
          600: "#1d4ed8",
          700: "#1e40af",
          900: "#0b1e3f",
        },
      },
    },
  },
  plugins: [],
};
