/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // These will be overridden by inline styles from business_config.json
        primary: '#3B82F6',
        secondary: '#10B981',
        accent: '#F59E0B',
      },
    },
  },
  plugins: [],
}
