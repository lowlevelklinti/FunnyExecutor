import { defineConfig } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";
import pkg from "./package.json";

export default defineConfig({
  base: "./",
  plugins: [svelte()],
  clearScreen: false,
  define: {
    APP_VERSION: JSON.stringify(pkg.version),
  },
  server: {
    port: 5173,
  },
  build: {
    target: "esnext",
    minify: "esbuild",
    cssMinify: true,
    chunkSizeWarningLimit: 2500,
    rollupOptions: {
      output: {
        manualChunks: {
          monaco: ["monaco-editor/editor/editor.api"],
        },
      },
    },
  },
});
