import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { port: 5173, strictPort: true },
  build: {
    target: "es2022",
    // The 3D intro (three.js + drei) stays in its own lazy-loaded chunk:
    // it is only fetched after the workspace renders, so its size is expected.
    chunkSizeWarningLimit: 1200,
    rollupOptions: {
      output: {
        manualChunks: {
          three: ["three", "@react-three/fiber", "@react-three/drei"],
          icons: ["lucide-react"],
        },
      },
    },
  },
});
