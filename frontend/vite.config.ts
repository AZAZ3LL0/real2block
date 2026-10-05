import react from "@vitejs/plugin-react";
import { loadEnv } from "vite";
import { defineConfig } from "vitest/config";

export default defineConfig(({ mode }) => {
  // In docker the API is another service; locally it is uvicorn on :8000.
  const apiTarget = loadEnv(mode, ".", "VITE_").VITE_API_PROXY ?? "http://localhost:8000";
  return {
    plugins: [react()],
    server: {
      host: true,
      port: 5173,
      strictPort: true,
      proxy: { "/api": { target: apiTarget } },
    },
    build: { sourcemap: false },
    test: {
      environment: "jsdom",
      // e2e/*.spec.ts belong to Playwright.
      include: ["src/**/*.test.{ts,tsx}"],
      globals: true,
      setupFiles: ["src/test/setup.ts"],
      css: false,
    },
  };
});
