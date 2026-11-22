import react from '@vitejs/plugin-react'
//import { defineConfig } from 'vite'
import { configDefaults, defineConfig } from 'vitest/config'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],

  server: {
    host: '0.0.0.0',
    port: 5173,
    strictPort: true,
    origin: 'http://127.0.0.1:5173',

    proxy: {
      '/api': {
        target: 'http://backend:8001',
        changeOrigin: true,
        secure: false,
      },
    },
  },

  test: {
    environment: 'jsdom',
    setupFiles: './src/tests/setup.js',
    exclude: [...configDefaults.exclude, 'e2e/**'],
  },
})
