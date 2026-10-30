import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// The API is reached as /api on the page's own origin, so the browser never makes a
// cross-origin call. nginx does the same in the image (nginx.conf); both strip the
// prefix, so the API routes stay as they are.
const API_TARGET = "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  // The favicon set lives in docs/brand/ and is served from there, not copied.
  publicDir: "../docs/brand/favicon",
  server: {
    // The page imports the brand tokens and logo from docs/brand/, outside web/.
    fs: { allow: [".."] },
    proxy: {
      "/api": {
        target: API_TARGET,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
  test: {
    environment: "jsdom",
  },
});
