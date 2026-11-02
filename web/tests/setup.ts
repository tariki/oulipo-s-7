import '@testing-library/jest-dom/vitest';
import { cleanup, configure } from '@testing-library/react';
import { afterEach } from 'vitest';

// findBy・waitFor が待つ上限(既定は1秒)。並行に動かしたときの遅れで落ちないよう広げる
configure({ asyncUtilTimeout: 5_000 });

// グローバルを使わない設定のため、描画した部品をテストごとに自分で片付ける
afterEach(() => {
  cleanup();
});
