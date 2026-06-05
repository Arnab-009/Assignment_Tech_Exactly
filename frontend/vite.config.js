import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// During local development the API runs on :8000. We proxy /api so the browser
// sees a single origin (:5173) — this keeps the session cookie same-origin and
// avoids CORS entirely. In Docker, nginx performs the equivalent proxying.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
  },
})
