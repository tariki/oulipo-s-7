import { Link } from 'react-router';

/** このアプリについて。各節は「画面」の作業で作る(機能設計書「『このアプリについて』の構成」)。 */
export function AboutPage() {
  return (
    <main>
      <h1>このアプリについて</h1>
      <Link to="/">変換画面へ戻る</Link>
    </main>
  );
}
