import type { Config } from 'tailwindcss'

export default {
  darkMode: ['class'],
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        border: 'hsl(214.3 31.8% 91.4%)',
        background: 'hsl(0 0% 100%)',
        foreground: 'hsl(222.2 47.4% 11.2%)',
        brand: {
          DEFAULT: '#4f46e5',
          foreground: '#ffffff'
        }
      },
      boxShadow: {
        card: '0 10px 25px -10px rgba(0,0,0,0.25)'
      }
    }
  },
  plugins: []
} satisfies Config


