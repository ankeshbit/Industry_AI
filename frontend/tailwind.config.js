/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        industrial: {
          900: '#0F172A',
          800: '#1E293B',
          700: '#334155',
          600: '#475569',
          500: '#64748B',
          400: '#94A3B8',
          100: '#F1F5F9',
          50: '#F8FAFC',
        },
        brand: {
          500: '#0284C7',
          600: '#0369A1',
          700: '#075985',
        }
      }
    },
  },
  plugins: [],
}

