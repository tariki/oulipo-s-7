import { Suspense, lazy } from 'react';
import { Route, Routes } from 'react-router';

import { TransformPage } from './pages/TransformPage';

// 「このアプリについて」はライセンスの全文を含むため、開いたときだけ読み込む
const AboutPage = lazy(() =>
  import('./pages/AboutPage').then((module) => ({ default: module.AboutPage })),
);

/** ルーティング(/ と /about)。ルーターの種類は main.tsx とテストで選ぶ。 */
export function App() {
  return (
    <Routes>
      <Route path="/" element={<TransformPage />} />
      <Route
        path="/about"
        element={
          <Suspense fallback={<p>読み込み中…</p>}>
            <AboutPage />
          </Suspense>
        }
      />
    </Routes>
  );
}
