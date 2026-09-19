/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ministry: {
          dark: "#1e293b",
          primary: "#0f766e",
          accent: "#d97706",
          light: "#f8fafc",
        },
      },
    },
  },
  plugins: [],
};
