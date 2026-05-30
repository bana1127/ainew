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
        ink: "#1f2937",
        mist: "#f3f6f8",
        line: "#d9e1e8",
        pine: "#1f6f5b",
        coral: "#df6b57",
        amber: "#c48a24",
      },
    },
  },
  plugins: [],
};

export default config;

