import { type KeyboardEvent, useCallback, useEffect, useMemo, useRef } from 'react';

import type { TransformResponse } from '../api/types';
import { splitParagraphs } from '../segments/splitParagraphs';
import { ParagraphView } from './ParagraphView';
import styles from './ResultView.module.css';

interface ResultViewProps {
  id: string;
  result: TransformResponse;
  /** 文章を編集した後の古い結果か(薄く表示し、語は選べなくする)。 */
  isStale: boolean;
  /** 変換後の文章の見出しの横に置くもの(コピーのボタン)。 */
  actions?: React.ReactNode;
}

const TOKEN_SELECTOR = '[data-noun-token]';

/**
 * 元の文章と変換後の文章を並べて表示する(PCは左右、スマートフォンは変換後が先)。
 * 変換後の語は、Tabキーでは1回で入り、中では左右の矢印キーで移る(ロービングタブインデックス)。
 */
export function ResultView({ id, result, isStale, actions }: ResultViewProps) {
  const paragraphs = useMemo(() => splitParagraphs(result.segments), [result]);
  const replacedRef = useRef<HTMLDivElement>(null);

  // 最初の語だけを Tab で入れるようにする(1万語あっても Tab で結果を通り過ぎられるように)。
  // 結果を差し替えたときに Tab で入れる語が2つ以上にならないよう、全部を -1 に戻してから決める
  useEffect(() => {
    const tokens = replacedRef.current?.querySelectorAll<HTMLElement>(TOKEN_SELECTOR) ?? [];
    tokens.forEach((token, index) => {
      token.tabIndex = index === 0 ? 0 : -1;
    });
  }, [paragraphs, isStale]);

  // 段落を描き直さずに済むよう、tabIndex は DOM を直接切り替える
  const handleTokenKeyDown = useCallback((event: KeyboardEvent<HTMLButtonElement>) => {
    const step = { ArrowRight: 1, ArrowLeft: -1 }[event.key];
    const container = replacedRef.current;
    if (step === undefined || container === null) {
      return;
    }
    const tokens = Array.from(container.querySelectorAll<HTMLElement>(TOKEN_SELECTOR));
    const next = tokens[tokens.indexOf(event.currentTarget) + step];
    if (next === undefined) {
      return;
    }
    event.preventDefault();
    event.currentTarget.tabIndex = -1;
    next.tabIndex = 0;
    next.focus();
  }, []);

  return (
    <section
      id={id}
      className={isStale ? styles.stale : styles.result}
      aria-label="変換の結果"
      tabIndex={-1}
    >
      <div className={styles.replaced}>
        <div className={styles.heading}>
          <h2>変換後</h2>
          {actions}
        </div>
        <div ref={replacedRef} className={styles.text}>
          {paragraphs.map((paragraph) => (
            <ParagraphView
              key={paragraph.index}
              paragraph={paragraph}
              side="replaced"
              isSelectable={!isStale}
              onTokenKeyDown={handleTokenKeyDown}
            />
          ))}
        </div>
      </div>
      <div className={styles.original}>
        <div className={styles.heading}>
          <h2>元の文章</h2>
        </div>
        <div className={styles.text}>
          {paragraphs.map((paragraph) => (
            <ParagraphView
              key={paragraph.index}
              paragraph={paragraph}
              side="original"
              isSelectable={false}
              onTokenKeyDown={handleTokenKeyDown}
            />
          ))}
        </div>
      </div>
    </section>
  );
}
