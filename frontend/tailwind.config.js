/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        "primary": "#005da7",
        "on-primary": "#ffffff",
        "primary-container": "#2976c7",
        "on-primary-container": "#fdfcff",
        
        "secondary": "#4f5e7e",
        "on-secondary": "#ffffff",
        "secondary-container": "#cadaff",
        "on-secondary-container": "#505f7f",
        
        "tertiary": "#5c5c59",
        "on-tertiary": "#ffffff",
        "tertiary-container": "#757572",
        "on-tertiary-container": "#fefcf8",

        "error": "#ba1a1a",
        "on-error": "#ffffff",
        "error-container": "#ffdad6",
        "on-error-container": "#93000a",

        "background": "#fff8f5",
        "on-background": "#1f1b18",
        "surface": "#fff8f5",
        "on-surface": "#1f1b18",
        "surface-variant": "#ebe0dc",
        "on-surface-variant": "#414751",
        
        "outline": "#717783",
        "outline-variant": "#c1c7d3",

        "surface-container-highest": "#ebe0dc",
        "surface-container-high": "#f1e6e1",
        "surface-container": "#f7ece7",
        "surface-container-low": "#fdf1ed",
        "surface-container-lowest": "#ffffff",
      },
      borderRadius: {
        "DEFAULT": "0.25rem",
        "lg": "0.5rem",
        "xl": "0.75rem",
        "full": "9999px"
      },
      spacing: {
        "xl": "64px",
        "gutter": "24px",
        "base": "8px",
        "md": "24px",
        "lg": "40px",
        "sm": "12px",
        "container-max": "1280px",
        "xs": "4px"
      },
      fontFamily: {
        "body-md": ["Work Sans"],
        "body-sm": ["Work Sans"],
        "h2": ["Manrope"],
        "label-caps": ["Work Sans"],
        "body-lg": ["Work Sans"],
        "h3": ["Manrope"],
        "h1": ["Manrope"],
        "h1-mobile": ["Manrope"]
      },
      fontSize: {
        "body-md": ["16px", {"lineHeight": "1.6", "fontWeight": "400"}],
        "body-sm": ["14px", {"lineHeight": "1.5", "fontWeight": "400"}],
        "h2": ["32px", {"lineHeight": "1.3", "fontWeight": "600"}],
        "label-caps": ["12px", {"lineHeight": "1", "letterSpacing": "0.05em", "fontWeight": "600"}],
        "body-lg": ["18px", {"lineHeight": "1.6", "fontWeight": "400"}],
        "h3": ["24px", {"lineHeight": "1.4", "fontWeight": "500"}],
        "h1": ["48px", {"lineHeight": "1.2", "letterSpacing": "-0.02em", "fontWeight": "600"}],
        "h1-mobile": ["32px", {"lineHeight": "1.2", "fontWeight": "600"}]
      }
    },
  },
  plugins: [],
}
