/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // Calm, trustworthy fintech palette — deep ink + soft sage accent
        ink: {
          50: '#f6f7f8',
          100: '#eceef0',
          200: '#d5d9dd',
          300: '#b1b9c0',
          400: '#87929c',
          500: '#68757f',
          600: '#535e67',
          700: '#444d54',
          800: '#3a4146',
          900: '#23282c',
          950: '#16191c',
        },
        sage: {
          50: '#f4f8f5',
          100: '#e4efe6',
          200: '#cadfd0',
          300: '#a4c7ae',
          400: '#78a985',
          500: '#578c67',
          600: '#417050',
          700: '#355941',
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
        card: '0 1px 2px 0 rgb(22 25 28 / 0.04), 0 1px 3px 0 rgb(22 25 28 / 0.06)',
        raised: '0 4px 12px -2px rgb(22 25 28 / 0.08), 0 2px 4px -2px rgb(22 25 28 / 0.05)',
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
