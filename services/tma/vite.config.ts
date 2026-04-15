import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  base: process.env.VITE_APP_BASE_PATH || '/',
  plugins: [react()],
  server: {
    port: 5174,
    host: true,
    // In dev mode proxy /api/ to the local API container (port 8055)
    proxy: {
      '/api': {
        target: 'http://localhost:8055',
        rewrite: path => path.replace(/^\/api/, ''),
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
  },
})
