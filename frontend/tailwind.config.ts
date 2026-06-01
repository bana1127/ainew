import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Legacy tokens (kept for backwards compat, values updated)
        ink: "#1F1F24",
        mist: "#F8F5EF",
        line: "#E8E1D8",
        pine: "#7C6CF2",    // now primary lavender
        coral: "#B94A48",   // now danger red
        amber: "#C8A96A",   // now accent gold

        // New design tokens
        surface: "#FFFFFF",
        "surface-soft": "#FFFCF7",
        "text-muted": "#77716A",
        "border-soft": "#E8E1D8",
        primary: "#7C6CF2",
        "primary-soft": "#EEEAFE",
        accent: "#C8A96A",
        success: "#3F7D58",
        "success-soft": "#EAF5EE",
        warning: "#B9822B",
        "warning-soft": "#FFF3D9",
        danger: "#B94A48",
        "danger-soft": "#FCE9E8",
      },
      borderRadius: {
        card: "20px",
        btn: "14px",
      },
      boxShadow: {
        card: "0 1px 4px 0 rgba(31,31,36,0.06), 0 0 0 1px rgba(232,225,216,0.6)",
        "card-hover": "0 4px 16px 0 rgba(31,31,36,0.10), 0 0 0 1px rgba(232,225,216,0.6)",
        soft: "0 2px 8px 0 rgba(31,31,36,0.08)",
      },
      fontFamily: {
        sans: ["var(--font-sans)", "Pretendard", "Apple SD Gothic Neo", "ui-sans-serif", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;
