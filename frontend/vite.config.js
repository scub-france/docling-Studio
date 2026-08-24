import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { readFileSync } from 'fs'
import { fileURLToPath, URL } from 'node:url'

const pkg = JSON.parse(readFileSync('./package.json', 'utf-8'))
const apiProxyTarget = process.env.VITE_API_PROXY_TARGET || 'http://localhost:8000'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    // `@/` → `src/` : must mirror the `paths` alias declared in tsconfig.json
    // so Vite/Rollup resolve the same imports that vue-tsc type-checks.
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  define: {
    __APP_VERSION__: JSON.stringify(process.env.VITE_APP_VERSION || pkg.version),
  },
  server: {
    // host + allowedHosts : rend le dev server joignable depuis le container karate-agent (via host.docker.internal)
    host: true,
    port: 3000,
    allowedHosts: ['host.docker.internal'],
    proxy: {
      '/api': {
        target: apiProxyTarget,
        changeOrigin: true,
      },
      '/health': {
        target: apiProxyTarget,
        changeOrigin: true,
      },
    },
  },
})
