import { useId } from 'react';

import type { SenseItem } from '../api/types';
import styles from './SensePicker.module.css';

/** 語義の一覧の状態(取得は画面が行い、表示に要る分だけを受け取る)。 */
export type SensePickerState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'success'; senses: readonly SenseItem[] };

interface SensePickerProps {
  state: SensePickerState;
  /** いま使っている語義の概念ID。 */
  selectedSynsetId: string | undefined;
  /** 変換中。選び直しを受け付けない(ラジオボタンのフォーカスは失わせない)。 */
  isBusy: boolean;
  onSelect: (synsetId: string) => void;
  /** 一覧を取れなかったときに取り直す。 */
  onRetry: () => void;
}

/** 語義の選び直し([P1: F8])。語義ごとに見出し語と定義文を出し、選ぶとその語義で置き換え直す。 */
export function SensePicker({
  state,
  selectedSynsetId,
  isBusy,
  onSelect,
  onRetry,
}: SensePickerProps) {
  const name = useId();
  if (state.status === 'loading') {
    return <p className={styles.message}>語義の一覧を読み込んでいます…</p>;
  }
  if (state.status === 'error') {
    return (
      <div className={styles.failed}>
        <p className={styles.error}>{state.message}</p>
        <button type="button" className={styles.retry} onClick={onRetry}>
          もう一度読み込む
        </button>
      </div>
    );
  }
  return (
    <fieldset className={styles.picker}>
      <legend className={styles.legend}>語義を選び直す</legend>
      {state.senses.length === 1 && <p className={styles.message}>この語の語義は1つだけです。</p>}
      {state.senses.map((sense, i) => (
        <label key={sense.synsetId} className={styles.option} htmlFor={`${name}-${String(i)}`}>
          <input
            id={`${name}-${String(i)}`}
            type="radio"
            name={name}
            value={sense.synsetId}
            checked={sense.synsetId === selectedSynsetId}
            aria-disabled={isBusy}
            onChange={() => {
              if (!isBusy) {
                onSelect(sense.synsetId);
              }
            }}
          />
          <span className={styles.lemmas}>{sense.lemmas.join('・')}</span>
          <span className={styles.definition}>{sense.definition ?? '(定義文なし)'}</span>
        </label>
      ))}
    </fieldset>
  );
}
