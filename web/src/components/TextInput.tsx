import { useId } from 'react';

import { countChars } from '../text/countChars';
import styles from './TextInput.module.css';

interface TextInputProps {
  value: string;
  maxChars: number;
  onChange: (value: string) => void;
}

/** 入力欄と文字数(F1)。上限を超えたらメッセージを読み上げる。 */
export function TextInput({ value, maxChars, onChange }: TextInputProps) {
  const id = useId();
  const chars = countChars(value);
  const isOver = chars > maxChars;
  return (
    <div className={styles.field}>
      <label htmlFor={id}>文章</label>
      <textarea
        id={id}
        className={styles.textarea}
        value={value}
        rows={8}
        aria-invalid={isOver}
        aria-describedby={`${id}-count`}
        onChange={(event) => {
          onChange(event.target.value);
        }}
      />
      <p id={`${id}-count`} className={isOver ? styles.over : styles.count}>
        {chars.toLocaleString('ja-JP')} / {maxChars.toLocaleString('ja-JP')}
      </p>
      {/* 打鍵のたびに読み上げないよう、文字数ではなく上限超過だけを読み上げる */}
      <p className={styles.overMessage} aria-live="polite">
        {isOver ? `${maxChars.toLocaleString('ja-JP')}文字以内で入力してください` : ''}
      </p>
    </div>
  );
}
