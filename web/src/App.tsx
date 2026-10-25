import { Route, Routes } from 'react-router';

import { AboutPage } from './pages/AboutPage';
import { TransformPage } from './pages/TransformPage';

/** ルーティング(/ と /about)。ルーターの種類は main.tsx とテストで選ぶ。 */
export function App() {
  return (
    <Routes>
      <Route path="/" element={<TransformPage />} />
      <Route path="/about" element={<AboutPage />} />
    </Routes>
  );
}
