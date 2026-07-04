import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const apiTarget = process.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'
const allowedHosts = ['localhost', '127.0.0.1', '0.0.0.0', '.up.railway.app']

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 3000,
    strictPort: true,
    allowedHosts,
    proxy: {
      '/api': {
        target: apiTarget,
        changeOrigin: true,
        secure: false,
      }
    }
  },
  preview: {
    host: '0.0.0.0',
    port: Number(process.env.PORT || 3000),
    strictPort: true,
    allowedHosts,
  }
})
