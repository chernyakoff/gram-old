import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'
import uiPro from '@nuxt/ui-pro/vite'
import { runtimeEnv } from 'vite-plugin-runtime'



export default defineConfig({
  plugins: [
    vue(),
    uiPro(),
    runtimeEnv({
      generateTypes: true,
      generatedTypesPath: 'src',
      injectHtml: true,
      name: 'env', // window.env
    }),

    vueDevTools(),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    },
  },
})
