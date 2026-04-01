import tailwindcss from '@tailwindcss/vite'

export default defineNuxtConfig({
  compatibilityDate: '2025-03-27',
  devtools: { enabled: true },
  css: ['~/assets/css/main.css'],
  vite: {
    plugins: [tailwindcss()],
  },
  runtimeConfig: {
    databaseUrl: process.env.NUXT_DATABASE_URL || '',
  },
  typescript: {
    strict: true,
  },
  modules: ['@nuxtjs/sitemap', '@scalar/nuxt'],
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
  nitro: {
    experimental: { openAPI: true },
    openAPI: {
      production: 'runtime',
      meta: {
        title: 'Poliscope API',
        description: 'API publique Poliscope — debats parlementaires, scrutins, acteurs',
        version: '2.0.0',
      },
      ui: {
        scalar: {
          route: '/api/docs',
        },
      },
    },
  },
  routeRules: {
    '/api/debates': { headers: { 'cache-control': 'public, max-age=300' } },
    '/api/debates/**': { headers: { 'cache-control': 'public, max-age=300' } },
    '/api/deputies': { headers: { 'cache-control': 'public, max-age=3600' } },
    '/api/deputies/**': { headers: { 'cache-control': 'public, max-age=600' } },
    '/api/votes': { headers: { 'cache-control': 'public, max-age=300' } },
    '/api/votes/**': { headers: { 'cache-control': 'public, max-age=300' } },
  },
})
