import { Fragment, type KeyboardEvent, memo } from 'react';

import type { Paragraph } from '../segments/splitParagraphs';
import { NounToken } from './NounToken';
import styles from './ResultView.module.css';

interface ParagraphViewProps {
  paragraph: Paragraph;
  side: 'original' | 'replaced';
  isSelectable: boolean;
  onTokenKeyDown: (event: KeyboardEvent<HTMLButtonElement>) => void;
}

/**
 * 段落1つ。memo して、ほかの段落の変化で描き直さない。
 * 画面外の段落は content-visibility: auto で描画を省く(機能設計書「長文の表示」)。
 */
export const ParagraphView = memo(function ParagraphView({
  paragraph,
  side,
  isSelectable,
  onTokenKeyDown,
}: ParagraphViewProps) {
  return (
    <div className={styles.paragraph}>
      {paragraph.items.map((item, i) => {
        if (typeof item === 'string' || side === 'original') {
          // 位置は段落の中で変わらないため、添字を key にしてよい
          return <Fragment key={i}>{typeof item === 'string' ? item : item.original}</Fragment>;
        }
        return (
          <NounToken
            key={i}
            segment={item}
            isSelectable={isSelectable}
            onKeyDown={onTokenKeyDown}
          />
        );
      })}
    </div>
  );
});
