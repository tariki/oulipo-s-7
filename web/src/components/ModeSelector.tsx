import type { Mode } from '../api/types';
import styles from './Controls.module.css';

interface ModeSelectorProps {
  value: Mode;
  onChange: (mode: Mode) => void;
}

const OPTIONS: { value: Mode; label: string }[] = [
  { value: 'gojuon', label: '五十音順' },
  { value: 'concept', label: '概念版' },
];

/** ルールの選択(F2・F3)。 */
export function ModeSelector({ value, onChange }: ModeSelectorProps) {
  return (
    <fieldset className={styles.fieldset}>
      <legend>ルール</legend>
      {OPTIONS.map((option) => (
        <label key={option.value} className={styles.radio}>
          <input
            type="radio"
            name="mode"
            value={option.value}
            checked={value === option.value}
            onChange={() => {
              onChange(option.value);
            }}
          />
          {option.label}
        </label>
      ))}
    </fieldset>
  );
}
