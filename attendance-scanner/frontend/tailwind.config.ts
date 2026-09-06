/** @type {import("tailwindcss").Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: "#1E1B4B",
          light: "#312E81",
          dark: "#13104F",
        },
        accent: {
          DEFAULT: "#F5B301",
          light: "#FCD34D",
          dark: "#D97706",
        },
        success: "#1F9D55",
        error: "#DC2626",
        surface: "#FAF9F6",
      },
      fontFamily: {
        display: ["Sora", "sans-serif"],
        body: ["Inter", "sans-serif"],
      },
      animation: {
        "fade-in": "fadeIn 0.3s ease-out",
        "slide-up": "slideUp 0.3s ease-out",
        "pulse-ring": "pulseRing 2s ease-in-out infinite",
      },
      keyframes: {
        fadeIn: { from: { opacity: "0" }, to: { opacity: "1" } },
        slideUp: { from: { transform: "translateY(20px)", opacity: "0" }, to: { transform: "translateY(0)", opacity: "1" } },
        pulseRing: {
          "0%, 100%": { boxShadow: "0 0 0 0 rgba(245,179,1,0.4)" },
          "50%": { boxShadow: "0 0 0 16px rgba(245,179,1,0)" },
        },
      },
    },
  },
  plugins: [],
};
