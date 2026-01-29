import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  // Load .env file from project root (one level up)
  const rootDir = path.resolve(__dirname, '..')
  const env = loadEnv(mode, rootDir, '')
  
  return {
    plugins: [react()],
    // Expose environment variables that start with VITE_
    define: {
      'import.meta.env.VITE_PBI_EMBED_URL': JSON.stringify(env.VITE_PBI_EMBED_URL),
      'import.meta.env.VITE_API_BASE': JSON.stringify(env.VITE_API_BASE),
    },
    server: {
      host: '127.0.0.1',
      port: 8088,
      strictPort: true,
      hmr: {
        host: '127.0.0.1',
        port: 8088,
      },
      proxy: {
        '/api': {
          target: 'http://127.0.0.1:8000',
          changeOrigin: true,
        },
        '/cluster': {
          target: 'http://127.0.0.1:8000',
          changeOrigin: true,
        },
        '/risk': {
          target: 'http://127.0.0.1:8000',
          changeOrigin: true,
        },
      },
    },
  }
})
