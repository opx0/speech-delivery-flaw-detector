import { loadEnv } from "vite";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { mockApiPlugin } from "./mock/plugin.ts";

export default defineConfig(({ mode }) => ({
  envDir: "..",
  plugins: [react(), ...(mode === "demo" ? [mockApiPlugin()] : [])],
  server: {
    proxy:
      mode !== "demo"
        ? {
            "/api":
              process.env.SPEECH_API_URL ||
              loadEnv(mode, "..", "SPEECH_").SPEECH_API_URL ||
              "http://127.0.0.1:8000",
          }
        : undefined,
  },
  resolve: {
    alias: {
      "@": "/src",
    },
  },
}));
