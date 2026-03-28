import { fileURLToPath } from 'node:url'
import { config } from 'dotenv'
import { defineConfig, devices } from '@playwright/test'
import type { ConfigOptions } from '@nuxt/test-utils/playwright'

// Load .env from monorepo root
config({ path: '../../.env' })

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
