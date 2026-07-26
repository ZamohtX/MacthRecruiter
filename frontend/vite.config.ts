import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const backend = env.BACKEND_URL ?? "http://localhost:8000";

  return {
    plugins: [react(), tailwindcss()],
    server: {
      port: 5173,
      // Proxy em vez de CORS: no dev o navegador vê tudo na mesma origem, então
      // não há preflight nem necessidade de afrouxar `CORS_ORIGINS` no backend.
      proxy: {
        "/api": { target: backend, changeOrigin: true },
        "/health": { target: backend, changeOrigin: true },
      },
    },
    build: { outDir: "dist", sourcemap: true },
  };
});
