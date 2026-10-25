import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterEach } from 'vitest';

// グローバルを使わない設定のため、描画した部品をテストごとに自分で片付ける
afterEach(() => {
  cleanup();
});
