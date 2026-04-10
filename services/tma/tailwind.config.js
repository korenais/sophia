/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: '#1A1C24',
        surface: '#22252F',
        raised: '#2A2E3A',
        border: '#363B4F',
        gold: '#C9A84C',
        'gold-light': '#E3C96A',
        'gold-dim': 'rgba(201,168,76,0.12)',
        cream: '#EDE9E3',
        muted: '#7A8099',
        danger: '#E05252',
        success: '#4CAF7A',
      },
      fontFamily: {
        display: ['"Cormorant Garamond"', 'Georgia', 'serif'],
        body: ['"Jost"', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
