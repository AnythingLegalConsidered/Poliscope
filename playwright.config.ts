import { fileURLToPath } from 'node:url'
import { defineConfig, devices } from '@playwright/test'
import type { ConfigOptions } from '@nuxt/test-utils/playwright'

// Ensure NUXT_DATABASE_URL is set for the test server
process.env.NUXT_DATABASE_URL ??= 'postgresql://poliscope:poliscope_dev@localhost:5432/poliscope'

export default defineConfig<ConfigOptions>({
  testDir: './e2e',
  timeout: 60000,
  use: {
    nuxt: {
      rootDir: fileURLToPath(new URL('.', import.meta.url)),
    },
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
})
