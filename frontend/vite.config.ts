import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, ".", "VITE_");
  const base = env.VITE_PAGES_BASE || "/kiraorder/";
  if (!base.startsWith("/") || !base.endsWith("/") || base.includes("..") || base.includes("//") || /[?#]/.test(base))
    throw new Error("VITE_PAGES_BASE must be an absolute path with a trailing slash.");
  return {
    // Production configuration retains the competition project's asset prefix.
    base,
    plugins: [react(), tailwindcss()],
    server: { port: 5173, strictPort: true },
    build: {
      target: "es2022",
      // The 3D intro (three.js + drei) stays in its own lazy-loaded chunk:
      // it is fetched only when the introduction is opened.
      chunkSizeWarningLimit: 1200,
      rollupOptions: {
        output: {
          // Shared React/runtime dependencies must not be absorbed by the 3D chunk.
          onlyExplicitManualChunks: true,
          manualChunks(id) {
            if (/\/node_modules\/(react|react-dom|scheduler)\//.test(id)) return "react-vendor";
            if (/\/node_modules\/(three|@react-three|three-stdlib)\//.test(id)) return "three";
            if (id.includes("/node_modules/lucide-react/")) return "icons";
          },
        },
      },
    },
  };
});
