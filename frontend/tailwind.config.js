/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Inter"', '"Noto Sans JP"', 'sans-serif'],
        serif: ['"Noto Serif JP"', 'serif'],
      },
      colors: {
        brand: {
          50: '#f6f6f6',
          900: '#111111',
          950: '#0a0a0a',
        }
      },
      animation: {
        'fade-in': 'fadeIn 1s ease-out',
        'loading-line': 'loadingLine 1.5s ease-in-out infinite',
      },
    },
  },
  plugins: [],
}
