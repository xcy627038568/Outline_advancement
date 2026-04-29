/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        dark: '#121212',
        darker: '#0a0a0a',
        gold: '#d4af37',
        military: '#4b5320'
      }
    },
  },
  plugins: [],
}
