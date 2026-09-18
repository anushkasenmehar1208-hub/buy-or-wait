/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // Calm, trustworthy fintech palette — deep ink + soft sage accent.
        // Ink/sage values live in CSS variables (src/index.css) so `darkMode: class`
        // swaps the palette globally; `rgb(var(--ink-50) / <alpha-value>)` keeps
        // opacity utilities (bg-ink-50/90, text-ink-700, …) fully functional.
        ink: {
          50: 'rgb(var(--ink-50) / <alpha-value>)',
          100: 'rgb(var(--ink-100) / <alpha-value>)',
          200: 'rgb(var(--ink-200) / <alpha-value>)',
          300: 'rgb(var(--ink-300) / <alpha-value>)',
          400: 'rgb(var(--ink-400) / <alpha-value>)',
          500: 'rgb(var(--ink-500) / <alpha-value>)',
          600: 'rgb(var(--ink-600) / <alpha-value>)',
          700: 'rgb(var(--ink-700) / <alpha-value>)',
          800: 'rgb(var(--ink-800) / <alpha-value>)',
          900: 'rgb(var(--ink-900) / <alpha-value>)',
          950: 'rgb(var(--ink-950) / <alpha-value>)',
        },
        // Opaque surface used for cards/header (white in light, raised dark in dark).
        surface: 'rgb(var(--surface) / <alpha-value>)',
        sage: {
          50: '#f4f8f5',
          100: '#e4efe6',
          200: '#cadfd0',
          300: '#a4c7ae',
          400: '#78a985',
          500: 'rgb(var(--sage-500) / <alpha-value>)',
          600: 'rgb(var(--sage-600) / <alpha-value>)',
          700: 'rgb(var(--sage-700) / <alpha-value>)',
          800: '#2c4736',
          900: '#253b2e',
        },
        amber: {
          400: '#fbbf24',
          500: '#f59e0b',
          600: '#d97706',
        },
        rose: {
          400: '#fb7185',
          500: '#f43f5e',
          600: '#e11d48',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'Segoe UI', 'sans-serif'],
      },
      boxShadow: {
        card: 'var(--shadow-card)',
        raised: 'var(--shadow-raised)',
      },
      keyframes: {
        'fade-in': {
          from: { opacity: '0', transform: 'translateY(4px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        shimmer: {
          '100%': { transform: 'translateX(100%)' },
        },
      },
      animation: {
        'fade-in': 'fade-in 0.25s ease-out',
      },
    },
  },
  plugins: [],
}
