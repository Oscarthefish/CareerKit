/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // Warm-tinted neutral scale (replaces Tailwind's default cool gray)
        // so every existing gray-* utility across the app - touched or not
        // in this pass - picks up the same foundation automatically.
        gray: {
          50: '#faf9f7',
          100: '#f5f4f1',
          200: '#e7e4df',
          300: '#d9d5cd',
          400: '#b5afa4',
          500: '#9c968c',
          600: '#807a70',
          700: '#6b6660',
          800: '#433f3a',
          900: '#1f1d1a',
          950: '#141311',
        },
        brand: {
          50: '#f0f7ff',
          100: '#e0effe',
          200: '#bae0fd',
          300: '#7dc6fb',
          400: '#38a8f7',
          500: '#0e8ce8',
          600: '#026ec6',
          700: '#0358a1',
          800: '#074a84',
          900: '#0c3f6e',
          950: '#082849',
        },
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
    },
  },
  plugins: [],
}
