import { Link } from 'react-router';

/** 変換画面。入力欄と結果の表示は「画面」の作業で作る。 */
export function TransformPage() {
  return (
    <main>
      <h1>S+7メーカー</h1>
      <p>文章中の名詞を、辞書でN個先の語に置き換えます。</p>
      <Link to="/about">このアプリについて</Link>
    </main>
  );
}
