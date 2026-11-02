import { defineConfig, mergeConfig } from 'vitest/config';

import viteConfig from './vite.config.ts';

export default mergeConfig(
  viteConfig,
  defineConfig({
    test: {
      environment: 'jsdom',
      include: ['tests/unit/**/*.test.{ts,tsx}'],
      setupFiles: ['tests/setup.ts'],
      // カバレッジつきで全ファイルを並行に動かすと、各ファイルの最初のテスト(jsdom の用意と画面の
      // 取り込みを含む)が既定の5秒を超えることがある(Dev Container で計測)。遅いテストを隠さないよう、
      // 待つ上限だけを広げる
      testTimeout: 15_000,
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
