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
    // Emit ONE shared CSS bundle (style.css) for all entries. base.html
    // links it once via <link href="/static/island/style.css">. Default
    // (true) splits CSS per chunk and names the file after whichever shared
    // chunk imports the global stylesheet (e.g. LiveRegion.css), which
    // breaks the deterministic link path Jinja needs.
    cssCodeSplit: false,
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
