/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,jsx}"],
  prefix: "tw-",
  corePlugins: { preflight: false },
  theme: {
    extend: {
      colors: {
        ai: { blue: "#2563eb", violet: "#7c3aed" }
      },
      boxShadow: {
        aurora: "0 24px 80px rgba(55, 92, 190, .16)"
      }
    }
  },
  plugins: []
};
