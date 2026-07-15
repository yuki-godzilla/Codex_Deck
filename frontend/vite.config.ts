import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const deck = loadEnv(mode, ".", "CODEX_DECK_");
  const apiPort = deck.CODEX_DECK_API_PORT || "43174";

  return {
    plugins: [react()],
    server: {
      host: deck.CODEX_DECK_BIND_HOST || "127.0.0.1",
      port: Number(deck.CODEX_DECK_UI_PORT || "43173"),
      proxy: {
        "/api": {
          target: `http://127.0.0.1:${apiPort}`,
          ws: true,
        },
        "/healthz": `http://127.0.0.1:${apiPort}`,
      },
    },
  };
});
