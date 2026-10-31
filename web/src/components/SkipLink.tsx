import styles from './SkipLink.module.css';

interface SkipLinkProps {
  targetId: string;
}

/** 結果へのスキップリンク(機能設計書「キーボード操作」)。フォーカスしたときだけ見える。 */
export function SkipLink({ targetId }: SkipLinkProps) {
  return (
    <a className={styles.skipLink} href={`#${targetId}`}>
      結果へ移動
    </a>
  );
}
