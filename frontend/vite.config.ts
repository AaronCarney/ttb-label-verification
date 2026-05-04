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
    // Emit one CSS bundle per entry (single.css, batch.css) so the Jinja
    // shell's <link href="/static/island/{name}.css"> resolves. Default
    // (true) splits CSS by chunk and would name the file after whichever
    // shared chunk imports the global stylesheet (e.g. LiveRegion.css).
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
