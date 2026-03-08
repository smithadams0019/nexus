/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        'nexus-primary': '#6C63FF',
        'nexus-dark': '#0A0A1A',
        'nexus-surface': '#1A1A2E',
        'nexus-border': '#2A2A3E',
      },
    },
  },
  plugins: [],
};
