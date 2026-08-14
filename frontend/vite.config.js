import { defineConfig } from 'vite'
import uni from '@dcloudio/vite-plugin-uni'

export default defineConfig({
  plugins: [uni()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      // H5 本地开发时，把 /api 代理到后端，避免跨域与手填地址
      '/api': {
        target: process.env.VITE_API_TARGET || 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
})
