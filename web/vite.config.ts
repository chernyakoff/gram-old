import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
//import vueDevTools from 'vite-plugin-vue-devtools'
import ui from '@nuxt/ui/vite'

import { runtimeEnv } from 'vite-plugin-runtime'
/*
const NuxtUIResolver = () => {
  return (name: string) => {
    console.log(name)
    if (!name.startsWith('U') || name.length === 1) return
    const importName = name.slice(1) // UButton -> Button
    return { name: importName, from: '@nuxt/ui' }
  }
}
 */
export default defineConfig({
  plugins: [
    vue(),
    ui({
      components: {
        dirs: [],
        // resolvers: [NuxtUIResolver()],
        dts: true,
      },

      ui: {
        colors: {
          primary: 'teal',
          secondary: 'purple',
          neutral: 'zinc',
        },
      },
    }),

    runtimeEnv({
      generateTypes: true,
      generatedTypesPath: 'src',
      injectHtml: true,
      name: 'env', // window.env
    }),
    // vueDevTools(),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
})
