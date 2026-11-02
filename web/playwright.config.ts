import { defineConfig, devices } from '@playwright/test';

const PORT = 4173;

/** 画面の性能テストだけを動かす(npm run e2e:performance)。ほかのテストと並べると遅れるため、別に1つずつ動かす。 */
const IS_PERFORMANCE = process.env.E2E_PERFORMANCE === '1';
const PERFORMANCE_SPEC = '**/performance.spec.ts';

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
  projects: IS_PERFORMANCE
    ? [{ name: 'performance', testMatch: PERFORMANCE_SPEC, use: { ...devices['Desktop Chrome'] } }]
    : [
        {
          name: 'desktop-chromium',
          testIgnore: PERFORMANCE_SPEC,
          use: { ...devices['Desktop Chrome'] },
        },
        {
          name: 'mobile-360',
          testIgnore: PERFORMANCE_SPEC,
          use: {
            ...devices['Desktop Chrome'],
            viewport: { width: 360, height: 740 },
            hasTouch: true,
          },
        },
        ...(process.env.CI
          ? [
              {
                name: 'desktop-webkit',
                testIgnore: PERFORMANCE_SPEC,
                use: { ...devices['Desktop Safari'] },
              },
            ]
          : []),
      ],
  webServer: {
    command: `npm run build && npx vite preview --port ${String(PORT)} --strictPort`,
    port: PORT,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
