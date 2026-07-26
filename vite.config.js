import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "node:path";

export default defineConfig({
  // The FastAPI app is served below /resume-ai/. Relative asset URLs keep
  // dynamic Vite chunks inside static/ai-login/ in local and cloud deploys.
  base: "./",
  plugins: [react()],
  build: {
    outDir: resolve(process.cwd(), "app/static/ai-login"),
    emptyOutDir: true,
    cssCodeSplit: true,
    rollupOptions: {
      input: resolve(process.cwd(), "src/main.jsx"),
      output: {
        entryFileNames: "auth-login.js",
        chunkFileNames: "chunks/[name]-[hash].js",
        assetFileNames: "auth-login.[ext]",
        // Keep React's dispatcher in one vendor module. Lazy Lottie and
        // particle modules must not create a circular import back into the
        // application entry, or React hooks can resolve against no dispatcher.
        manualChunks(id) {
          if (id.includes("node_modules/react/") || id.includes("node_modules/react-dom/") || id.includes("node_modules/scheduler/")) {
            return "react-runtime";
          }
        }
      }
    }
  }
});
