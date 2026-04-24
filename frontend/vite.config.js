import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  esbuild: {
    jsx: 'automatic', // React 18 JSX transform for .tsx compositions
  },
  optimizeDeps: {
    include: ['react', 'react-dom', 'react-dom/client', '@remotion/player'],
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
