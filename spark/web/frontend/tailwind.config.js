/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        spark: {
          bg: '#080c14',
          card: '#0d1117',
          border: 'rgba(99, 196, 255, 0.07)',
          accent: '#63c4ff',
          'accent-dim': 'rgba(99, 196, 255, 0.12)',
          text: '#e6edf3',
          muted: '#8899aa',
          dim: '#4a5568',
        },
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'monospace'],
        body: ['Space Grotesk', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
