import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import basicSsl from "@vitejs/plugin-basic-ssl";

export default defineConfig(({ command, mode }) => ({
  plugins: [
    react(),
    // HTTPS plugin — enables camera on phone over self-signed cert
    basicSsl(),
  ],
  server: {
    host: "0.0.0.0",
    port: 5173,
    https: true,   // self-signed cert auto-generated — no install needed
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
  build: { outDir: "dist", sourcemap: false },
  // Allow tesseract.js worker to load properly
  optimizeDeps: {
    exclude: ["tesseract.js"],
  },
}));
