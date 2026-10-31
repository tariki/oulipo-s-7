import { defineConfig, devices } from '@playwright/test';

const PORT = 4173;

/**
 * E2Eテスト。ビルドした画面を vite preview で配信し、APIは各テストで page.route のモックを返す
 * (辞書とサーバーに依存しないため。tests/e2e/fixtures/api.ts)。
 * CI(main.yml)では PC幅の WebKit も動かす。
 */
export default defineConfig({
  testDir: 'tests/e2e',
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? 'github' : 'list',
  use: {
    baseURL: `http://localhost:${String(PORT)}`,
    trace: 'retain-on-failure',
  },
  projects: [
    { name: 'desktop-chromium', use: { ...devices['Desktop Chrome'] } },
    {
      name: 'mobile-360',
      use: { ...devices['Desktop Chrome'], viewport: { width: 360, height: 740 }, hasTouch: true },
    },
    ...(process.env.CI ? [{ name: 'desktop-webkit', use: { ...devices['Desktop Safari'] } }] : []),
  ],
  webServer: {
    command: `npm run build && npx vite preview --port ${String(PORT)} --strictPort`,
    port: PORT,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
