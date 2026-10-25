import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

// 開発時は /api と /healthz をサーバー(Uvicorn)へ中継する
const API_ORIGIN = 'http://localhost:8000';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      '/api': API_ORIGIN,
      '/healthz': API_ORIGIN,
    },
    fs: {
      // about/sources.ts が web/ の外(../licenses/、../data/dictionary-history.md)を ?raw で読むため。
      // --host で外から見えるため、リポジトリ全体ではなく必要なディレクトリだけを許す
      allow: ['.', '../licenses', '../data'],
    },
  },
});
