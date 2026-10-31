import styles from './StatusBanner.module.css';

interface StatusBannerProps {
  tone: 'notice' | 'error';
  message: string;
}

/**
 * 「準備中です」、時間切れ、エラー、文章の変更などの表示。
 * エラーは alert で読み上げる。それ以外の知らせは、画面の読み上げ用の領域(常に DOM にある)が伝える
 * (後から挿入した status の領域は、読み上げソフトによっては読まれないため)。
 */
export function StatusBanner({ tone, message }: StatusBannerProps) {
  return (
    <p
      className={tone === 'error' ? styles.error : styles.notice}
      role={tone === 'error' ? 'alert' : undefined}
    >
      {message}
    </p>
  );
}
