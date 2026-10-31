import { Link, NavLink } from 'react-router';

import styles from './SiteHeader.module.css';
import { Wordmark } from './Wordmark';

interface SiteHeaderProps {
  /** 「S+7」を h1 にするか(変換画面)。ほかのページはページ名を h1 にする。 */
  isPageHeading: boolean;
}

/**
 * 両ページに共通の見出し(プロダクト要求定義書「画面の見た目」)。
 * 暗い帯に「S+7」とメニュー、その下の白地にアプリ名と一言の説明を置く。
 */
export function SiteHeader({ isPageHeading }: SiteHeaderProps) {
  const Title = isPageHeading ? 'h1' : 'div';
  return (
    <header>
      <div className={styles.band}>
        <div className={styles.inner}>
          <Title className={styles.title}>
            <Link to="/" className={styles.home}>
              <Wordmark />
            </Link>
          </Title>
          <nav aria-label="ページ" className={styles.nav}>
            <NavLink to="/" end className={styles.transform}>
              変換する
            </NavLink>
            <NavLink to="/about" className={styles.about}>
              このアプリについて
            </NavLink>
            <a href="/api/docs" className={styles.api}>
              API
            </a>
          </nav>
        </div>
      </div>
      <p className={styles.tagline}>
        <span className={styles.inner}>
          S+7メーカー ― 文章の名詞を、辞書でN個先の名詞に置き換える
        </span>
      </p>
    </header>
  );
}
