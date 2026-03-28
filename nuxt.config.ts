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
  modules: ['@nuxtjs/sitemap'],
  site: {
    url: process.env.NUXT_SITE_URL || 'https://poliscope.fr',
    name: 'Poliscope',
  },
  app: {
    head: {
      htmlAttrs: { lang: 'fr' },
      charset: 'utf-8',
      viewport: 'width=device-width, initial-scale=1',
      titleTemplate: '%s — Poliscope',
      meta: [
        { name: 'description', content: "Explorez les débats et l'activité des députés de l'Assemblée nationale" },
      ],
    },
  },
  sitemap: {
    sources: ['/api/__sitemap__/urls'],
  },
  routeRules: {
    '/api/debates': { cache: { maxAge: 300 } },
    '/api/debates/**': { cache: { maxAge: 300 } },
    '/api/deputies': { cache: { maxAge: 3600 } },
    '/api/deputies/**': { cache: { maxAge: 600 } },
  },
})
