import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tsconfigPaths from "vite-tsconfig-paths";

const DEFAULT_MODAL_URL = "https://sixscripts--agent-arena-backend-fastapi-app.modal.run";
const rawModalUrl = process.env.VITE_MODAL_URL;

if (rawModalUrl) {
  const cleaned = rawModalUrl
    .trim()
    .replace(/^VITE_MODAL_URL\s*=\s*/i, "")
    .replace(/^['"]|['"]$/g, "")
    .replace(/\/+$/, "");

  process.env.VITE_MODAL_URL = /^https?:\/\//i.test(cleaned)
    ? cleaned
    : DEFAULT_MODAL_URL;
}

// https://vite.dev/config/
export default defineConfig({
  build: {
    sourcemap: 'hidden',
  },
  plugins: [
    react({
      babel: {
        plugins: [
          'react-dev-locator',
        ],
      },
    }),
    tsconfigPaths()
  ],
})
