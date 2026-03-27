import tailwindcss from '@tailwindcss/vite'

export default defineNuxtConfig({
  compatibilityDate: '2025-03-27',
  devtools: { enabled: true },
  css: ['~/assets/css/main.css'],
  vite: {
    plugins: [tailwindcss()],
  },
  runtimeConfig: {
    databaseUrl: '', // Auto-mapped from NUXT_DATABASE_URL
  },
  typescript: {
    strict: true,
  },
})
