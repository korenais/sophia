import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          // Разделяем vendor библиотеки на отдельные чанки
          'react-vendor': ['react', 'react-dom'],
          'mui-vendor': ['@mui/material', '@mui/icons-material', '@emotion/react', '@emotion/styled'],
          'mui-grid-vendor': ['@mui/x-data-grid'],
        },
      },
    },
    // Увеличиваем лимит предупреждения до 1000 KB (vendor чанки могут быть большими)
    chunkSizeWarningLimit: 1000,
  },
})


