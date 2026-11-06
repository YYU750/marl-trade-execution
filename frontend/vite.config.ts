import { defineConfig } from 'vite'

export default defineConfig({
  base: './',
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('/node_modules/zrender/')) return 'chart-renderer'
          if (id.includes('/node_modules/echarts/')) return 'charts'
        },
      },
    },
  },
})
