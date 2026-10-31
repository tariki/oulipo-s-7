import { useEffect, useState } from 'react';

/** 「コピーしました」を消すまでの時間(同じ文言でも次のコピーで読み上げられるように)。 */
const MESSAGE_MS = 3_000;

import styles from './Controls.module.css';

interface CopyButtonProps {
  text: string;
  onCopy: () => void;
}

/** 変換後の文章をクリップボードにコピーする。解析のイベントは onCopy を受けた画面が送る。 */
export function CopyButton({ text, onCopy }: CopyButtonProps) {
  const [message, setMessage] = useState('');
  useEffect(() => {
    if (message === '') {
      return;
    }
    const timer = setTimeout(() => {
      setMessage('');
    }, MESSAGE_MS);
    return () => {
      clearTimeout(timer);
    };
  }, [message]);
  const handleClick = () => {
    // HTTPS でない環境などでは navigator.clipboard が無い。同期の例外も失敗として扱う
    Promise.resolve()
      .then(() => navigator.clipboard.writeText(text))
      .then(
        () => {
          setMessage('コピーしました');
          onCopy();
        },
        () => {
          setMessage('コピーできませんでした');
        },
      );
  };
  return (
    <span className={styles.copy}>
      <button type="button" className={styles.secondaryButton} onClick={handleClick}>
        コピー
      </button>
      <span role="status">{message}</span>
    </span>
  );
}
