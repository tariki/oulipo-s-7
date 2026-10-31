import styles from './Wordmark.module.css';

/**
 * 見出しの帯の「S+7」(プロダクト要求定義書「画面の見た目」)。
 * ウェブフォントを読み込まずに済むよう、縦長の太い線で描いた自前の SVG にする。色は文字色に従う。
 */
export function Wordmark() {
  return (
    <svg
      className={styles.wordmark}
      viewBox="0 0 280 160"
      role="img"
      aria-label="S+7メーカー"
      fill="none"
      stroke="currentColor"
      strokeWidth={28}
      strokeLinejoin="round"
    >
      <path d="M76 40V28H20v52h44v52H8v-12" />
      <path d="M140 52v56M112 80h56" />
      <path d="M200 28h66l-44 118" />
    </svg>
  );
}
