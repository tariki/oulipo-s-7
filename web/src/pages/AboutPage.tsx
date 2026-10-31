import { Link } from 'react-router';

import { parseDictionaryHistory } from '../about/parseDictionaryHistory';
import { DICTIONARY_HISTORY, LICENSE_TEXTS } from '../about/sources';
import styles from './AboutPage.module.css';

/** 不適切な語の報告の窓口(GitHubのIssueのテンプレート)。 */
const REPORT_URL =
  'https://github.com/tariki/oulipo-s-7/issues/new?template=excluded-word-report.yml';

/** このアプリについて(機能設計書「『このアプリについて』の構成」)。 */
export function AboutPage() {
  const releases = parseDictionaryHistory(DICTIONARY_HISTORY);
  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1>このアプリについて</h1>
        <Link to="/">変換画面へ戻る</Link>
      </header>
      <main className={styles.main}>
        <nav aria-label="目次">
          <ul className={styles.toc}>
            <li>
              <a href="#about">S+7法とは</a>
            </li>
            <li>
              <a href="#notes">結果について</a>
            </li>
            <li>
              <a href="#report">不適切な語の報告</a>
            </li>
            <li>
              <a href="#credits">出典とライセンス</a>
            </li>
            <li>
              <a href="#dictionary-history">辞書バージョンの更新履歴</a>
            </li>
            <li>
              <a href="#api-terms">APIの利用規約</a>
            </li>
            <li>
              <a href="#privacy">プライバシーポリシー</a>
            </li>
          </ul>
        </nav>

        <section id="about" aria-labelledby="about-heading">
          <h2 id="about-heading">S+7法とは</h2>
          <p>
            S+7法は、フランスの文学グループ「ウリポ(OuLiPo)」が考えた言葉遊びです。文章中の名詞(S)を、辞書でその名詞の7つ後(+7)に載っている名詞に置き換えます。文の形は変わらず、意味だけが思いがけない方向にずれます。
          </p>
          <p>このアプリには2つのルールがあります。いくつ先に進むか(N)は1〜99で選べます。</p>
          <dl>
            <dt>五十音順</dt>
            <dd>
              日本語WordNetの名詞を読みの五十音順に並べた一覧で、N個先の語に置き換えます。リストの末尾を超えたら先頭に戻ります。
            </dd>
            <dt>概念版</dt>
            <dd>
              意味のつながり(概念の木)をたどり、同じ上位の概念を持つ「兄弟の概念」の中でN個先の概念の語に置き換えます。兄弟が無ければ1つ上の階層に上がります。
            </dd>
          </dl>
        </section>

        <section id="notes" aria-labelledby="notes-heading">
          <h2 id="notes-heading">結果について</h2>
          <ul>
            <li>
              置き換え先の語は、辞書から機械的に選んだものです。意図しない語や、ふさわしくない語が出ることがあります。
            </li>
            <li>
              語の読みは機械的に付けたもので、誤りがありえます(例:
              「生物」を「なまもの」と読むなど)。五十音順の並びにも影響します。
            </li>
            <li>
              読みの分からない語は、五十音順では置き換えません(概念版では置き換えます)。辞書に無い語は、どちらのルールでも置き換えません。
            </li>
          </ul>
        </section>

        <section id="report" aria-labelledby="report-heading">
          <h2 id="report-heading">不適切な語の報告</h2>
          <p>
            一般公開の出力としてふさわしくない語(差別語・卑語など)が出た場合は、
            <a href={REPORT_URL}>GitHubのIssue</a>
            からお知らせください。確認のうえ辞書から外し、辞書のバージョンを上げて反映します。
          </p>
        </section>

        <section id="credits" aria-labelledby="credits-heading">
          <h2 id="credits-heading">出典とライセンス</h2>
          <p>
            このアプリは、日本語WordNet 1.1(© NICT ほか)、SudachiDict と SudachiPy(© Works
            Applications Co., Ltd.、Apache License
            2.0)などを使っています。ライセンスの全文は次のとおりです。
          </p>
          {LICENSE_TEXTS.map((license) => (
            <details key={license.title} className={styles.license}>
              <summary>{license.title}</summary>
              <pre>{license.text}</pre>
            </details>
          ))}
        </section>

        <section id="dictionary-history" aria-labelledby="history-heading">
          <h2 id="history-heading">辞書バージョンの更新履歴</h2>
          <p>辞書のバージョンが変わると、同じ文章でも結果が変わることがあります。</p>
          {releases.map((release) => (
            <section key={release.version} aria-label={`バージョン ${release.version}`}>
              <h3>
                {release.version}({release.date})
              </h3>
              <ul>
                {release.changes.map((change) => (
                  <li key={change}>{change}</li>
                ))}
              </ul>
            </section>
          ))}
        </section>

        <section id="api-terms" aria-labelledby="api-terms-heading">
          <h2 id="api-terms-heading">APIの利用規約</h2>
          <p>
            変換のAPIは、認証なしで誰でも使えます。使い方は<a href="/api/docs">API仕様書</a>
            をご覧ください。
          </p>
          <ul>
            <li>
              利用制限(回数と文字数)を超える呼び出し、サービスの運営を妨げる使い方はしないでください。
            </li>
            <li>結果の正しさ・適切さ、サービスの継続は保証しません。</li>
            <li>
              利用制限やAPIの内容は、予告なく変えることがあります(互換性の方針はAPI仕様書に書いています)。
            </li>
            <li>結果を公開する場合は、出典(応答の attribution)を表示してください。</li>
          </ul>
        </section>

        <section id="privacy" aria-labelledby="privacy-heading">
          <h2 id="privacy-heading">プライバシーポリシー</h2>
          <ul>
            <li>
              入力した文章と変換の結果は、サーバーに保存しません。ログにも残しません(文字数だけを記録します)。
            </li>
            <li>
              利用状況を知るため、匿名のアクセス解析を行います(画面を開いた、変換した、コピーした、という出来事と、モード・N・文字数の区分・名詞の数)。文章や語は送りません。Cookieも使いません。
            </li>
            <li>
              利用制限のため、接続元IPアドレスを直近1分間だけメモリに持ちます。アプリのログには出しません。
            </li>
          </ul>
        </section>
      </main>
    </div>
  );
}
