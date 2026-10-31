import styles from './Controls.module.css';

interface TransformButtonProps {
  /** 入力が不正で押せない。 */
  isDisabled: boolean;
  /** 変換中。押しても何もしない(disabled にするとフォーカスを失うため aria-disabled にする)。 */
  isBusy: boolean;
  /** 準備中に押され、準備ができ次第変換する操作を保持しているか。 */
  isWaiting: boolean;
  /** 変換が1秒を超えたか。 */
  isSlow: boolean;
  onClick: () => void;
}

/** 変換の実行。処理中は押せない。準備中は「準備ができ次第変換します」。 */
export function TransformButton({
  isDisabled,
  isBusy,
  isWaiting,
  isSlow,
  onClick,
}: TransformButtonProps) {
  let label = '変換する';
  if (isWaiting) {
    label = '準備ができ次第変換します';
  } else if (isSlow) {
    label = '変換中…';
  }
  return (
    <button
      type="button"
      className={styles.button}
      disabled={isDisabled}
      aria-disabled={isBusy}
      onClick={() => {
        if (!isBusy) {
          onClick();
        }
      }}
    >
      {label}
    </button>
  );
}
