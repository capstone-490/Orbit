// Substantial AI assistance used;

import { defineConfig, devices } from '@playwright/test'

const FRONTEND_URL = 'http://localhost:5173'
const API_URL = 'http://localhost:8001'

export default defineConfig({
  testDir: './e2e',
  // Each test creates its own data, so tests can run in parallel
  expect: { timeout: 15_000 },
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: [['list'], ['html', { open: 'never' }]],

  use: {
    baseURL: FRONTEND_URL,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    timezoneId: 'UTC',
    locale: 'en-US',
  },

  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        permissions: ['clipboard-read', 'clipboard-write'],
      },
    },
  ],

  webServer: {
    command: 'pnpm exec vite --host localhost --port 5173 --strictPort',
    url: FRONTEND_URL,
    env: { VITE_API_URL: API_URL },
    // Don't reuse an existing server: it might not have VITE_API_URL set
    reuseExistingServer: false,
    timeout: 60_000,
  },
})
