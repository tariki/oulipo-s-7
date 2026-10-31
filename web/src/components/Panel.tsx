import { type ReactNode, useId } from 'react';

import styles from './Panel.module.css';

export type PanelTone = 'input' | 'original' | 'replaced' | 'plain';

interface PanelProps {
  title: string;
  tone: PanelTone;
  /** 中身の右上に置くもの(コピーのボタンなど)。 */
  actions?: ReactNode;
  /** 置き場所を決めるための class(結果の左右の並びなど)。 */
  className?: string;
  children: ReactNode;
}

/**
 * 色の面(プロダクト要求定義書「画面の見た目」)。PC では左端に縦書きの見出しを付け、
 * スマートフォンの幅では見出しを横書きにして上に置く。
 */
export function Panel({ title, tone, actions, className, children }: PanelProps) {
  const headingId = useId();
  return (
    <section
      aria-labelledby={headingId}
      className={classNames(styles.panel, styles[tone], className)}
    >
      <h2 id={headingId} className={styles.title}>
        {title}
      </h2>
      <div className={classNames(styles.body, actions !== undefined && styles.withActions)}>
        {actions !== undefined && <div className={styles.actions}>{actions}</div>}
        {children}
      </div>
    </section>
  );
}

function classNames(...names: (string | false | undefined)[]): string {
  return names.filter(Boolean).join(' ');
}
