import { defineConfig, mergeConfig } from 'vitest/config';

import viteConfig from './vite.config.ts';

export default mergeConfig(
  viteConfig,
  defineConfig({
    test: {
      environment: 'jsdom',
      include: ['tests/unit/**/*.test.{ts,tsx}'],
      setupFiles: ['tests/setup.ts'],
      coverage: {
        provider: 'v8',
        include: ['src/**/*.{ts,tsx}'],
        // main.tsx は描画の入口だけ。generated/ はOpenAPIからの自動生成
        exclude: ['src/main.tsx', 'src/api/generated/**'],
        thresholds: {
          lines: 80,
          functions: 80,
          branches: 80,
          statements: 80,
        },
      },
    },
  }),
);
