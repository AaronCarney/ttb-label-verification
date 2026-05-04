import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "node:path";

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: resolve(__dirname, "../app/ui/static/island"),
    emptyOutDir: true,
    manifest: false,
    sourcemap: true,
    rollupOptions: {
      input: {
        single: resolve(__dirname, "src/single.tsx"),
        batch: resolve(__dirname, "src/batch.tsx"),
      },
      output: {
        entryFileNames: "[name].js",
        assetFileNames: "[name][extname]",
        chunkFileNames: "chunks/[name]-[hash].js",
      },
    },
  },
});
