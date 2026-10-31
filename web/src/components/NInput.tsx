import { useId } from 'react';

import styles from './Controls.module.css';

interface NInputProps {
  value: number;
  min: number;
  max: number;
  onChange: (n: number) => void;
}

/** N を数値に直す。空や数字でなければ NaN(範囲外の値もそのまま返し、呼び出し側で判定する)。 */
function parseN(raw: string): number {
  return raw.trim() === '' ? Number.NaN : Number(raw);
}

/** N が整数で範囲内か。 */
export function isValidN(n: number, min: number, max: number): boolean {
  return Number.isInteger(n) && n >= min && n <= max;
}

/** N の入力(F5)。範囲外なら知らせる(変換ボタンは呼び出し側で押せなくする)。 */
export function NInput({ value, min, max, onChange }: NInputProps) {
  const id = useId();
  const isValid = isValidN(value, min, max);
  return (
    <div className={styles.nField}>
      <label htmlFor={id}>N</label>
      <input
        id={id}
        className={styles.nInput}
        type="number"
        inputMode="numeric"
        min={min}
        max={max}
        step={1}
        value={Number.isNaN(value) ? '' : value}
        aria-invalid={!isValid}
        aria-describedby={isValid ? undefined : `${id}-error`}
        onChange={(event) => {
          onChange(parseN(event.target.value));
        }}
      />
      {!isValid && (
        <span id={`${id}-error`} className={styles.error} role="alert">
          {min}〜{max}の整数で入力してください
        </span>
      )}
    </div>
  );
}
